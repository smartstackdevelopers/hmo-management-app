"""F2.12 communication delivery for F2.2+ reminders and workflow notifications.

Creates ``CommunicationDelivery`` outbox rows and dispatches synchronously where the
worker has an open transaction; Celery may call ``dispatch_pending_communication_deliveries``.
External providers only activate when environment variables are configured.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.communication.providers.email import get_email_adapter
from app.communication.providers.sms import get_sms_adapter
from app.core.config import get_settings
from app.db.models.communication import CommunicationDelivery, CommunicationUserPreference
from app.db.models.user import User

logger = logging.getLogger("hmore.reminders")


def _now() -> datetime:
    return datetime.now(timezone.utc)


VALID_CHANNELS = frozenset({"in_app", "email", "sms", "push"})


@dataclass(frozen=True)
class ReminderMessage:
    organisation_id: str
    recipient_user_id: str
    subject: str
    body: str
    channel: str = "in_app"
    """Row identity for CommunicationDelivery.target_* (reminder_record, operational_delivery, …)."""
    target_type: str = "reminder_record"
    target_id: str = ""
    """Must match CommunicationDelivery.idempotency_key (unique per org)."""
    idempotency_key: str = ""
    essential_operational: bool = True


@dataclass(frozen=True)
class DeliveryResult:
    success: bool
    provider: str
    detail: str


class NotificationProvider(Protocol):
    def send(self, session: Session, message: ReminderMessage) -> DeliveryResult: ...


def _get_prefs(session: Session, *, organisation_id: uuid.UUID, user_id: uuid.UUID) -> CommunicationUserPreference | None:
    return session.scalar(
        select(CommunicationUserPreference).where(
            CommunicationUserPreference.organisation_id == organisation_id,
            CommunicationUserPreference.user_id == user_id,
        )
    )


def _channel_allowed(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    user_id: uuid.UUID,
    channel: str,
    essential_operational: bool,
) -> bool:
    prefs = _get_prefs(session, organisation_id=organisation_id, user_id=user_id)
    if prefs is None:
        return True
    if channel == "in_app":
        return prefs.allow_in_app
    if channel == "email":
        if essential_operational:
            return True
        return prefs.allow_email and not prefs.marketing_opt_out
    if channel == "sms":
        if essential_operational:
            return True
        return prefs.allow_sms and not prefs.sms_suppressed and not prefs.marketing_opt_out
    if channel == "push":
        return bool(prefs.allow_push)
    return False


def _delivery_status_after_send(channel: str, accepted: bool, detail: str) -> tuple[str, bool]:
    """Return (terminal_status, success_flag_for_reminder_record).

    ``delivered`` is only used when we have a meaningful confirmation; otherwise
    ``provider_accepted`` records hand-off without implying handset delivery.
    """
    if not accepted:
        return "failed", False
    if channel == "email":
        if "queued" in detail.lower() or "accepted" in detail.lower():
            return "provider_accepted", True
        return "provider_accepted", True
    if channel == "sms":
        return "provider_accepted", True
    # in_app — stored as delivered once persisted.
    return "delivered", True


class CommunicationNotificationProvider:
    """Outbox + optional SMTP / Twilio; in-app rows are terminal ``delivered`` on write."""

    def send(self, session: Session, message: ReminderMessage) -> DeliveryResult:
        org_uuid = uuid.UUID(message.organisation_id)
        recipient_uuid = uuid.UUID(message.recipient_user_id)
        channel = (message.channel or "in_app").strip().lower()
        if channel not in VALID_CHANNELS:
            return DeliveryResult(success=False, provider="none", detail=f"Unsupported channel {channel}")

        if not message.idempotency_key:
            return DeliveryResult(success=False, provider="none", detail="idempotency_key is required")

        if not _channel_allowed(
            session,
            organisation_id=org_uuid,
            user_id=recipient_uuid,
            channel=channel,
            essential_operational=message.essential_operational,
        ):
            return DeliveryResult(
                success=False,
                provider="preferences",
                detail="Recipient channel disabled by communication preferences",
            )

        def _parse_target_uuid(raw: str | None) -> uuid.UUID:
            if not raw:
                return org_uuid
            try:
                return uuid.UUID(str(raw))
            except ValueError:
                # Composite automation keys (run:resource) are not UUIDs — fall back to org.
                return org_uuid

        if channel == "push":
            from app.push.delivery import enqueue_push_for_target

            target = _parse_target_uuid(message.target_id)
            queued = enqueue_push_for_target(
                session,
                organisation_id=org_uuid,
                recipient_user_id=recipient_uuid,
                target_type=message.target_type,
                target_id=target,
                idempotency_base=message.idempotency_key,
            )
            if not queued:
                return DeliveryResult(success=False, provider="push", detail="no_active_push_tokens")
            return DeliveryResult(
                success=True,
                provider="push_outbox",
                detail="queued_not_device_received",
            )

        idem = message.idempotency_key
        target_uuid = _parse_target_uuid(message.target_id)

        existing = session.scalar(
            select(CommunicationDelivery).where(
                CommunicationDelivery.organisation_id == org_uuid,
                CommunicationDelivery.idempotency_key == idem,
            )
        )
        if existing is not None:
            if existing.status in {"delivered", "provider_accepted"}:
                return DeliveryResult(success=True, provider=existing.provider_name or "outbox", detail="Duplicate idempotency — prior delivery recorded")
            delivery = existing
        else:
            delivery = CommunicationDelivery(
                organisation_id=org_uuid,
                target_type=message.target_type,
                target_id=target_uuid,
                recipient_user_id=recipient_uuid,
                channel=channel,
                status="created",
                subject=message.subject[:500] if message.subject else None,
                body=message.body,
                scheduled_at=_now(),
                idempotency_key=idem,
            )
            session.add(delivery)
            session.flush()

        delivery.status = "queued"
        session.flush()

        user = session.get(User, recipient_uuid)
        if user is None:
            delivery.status = "failed"
            delivery.last_error = "Recipient user missing"
            return DeliveryResult(success=False, provider="none", detail="Recipient user missing")

        settings = get_settings()
        delivery.status = "attempted"
        delivery.attempt_count += 1
        delivery.last_attempt_at = _now()

        if channel == "in_app":
            delivery.status = "delivered"
            delivery.provider_name = "in_app_store"
            delivery.last_error = None
            session.flush()
            return DeliveryResult(success=True, provider="in_app_store", detail="Message stored for in-app retrieval")

        if channel == "email":
            adapter = get_email_adapter(settings)
            ok, provider_name, detail = adapter.send(
                to_email=user.email,
                subject=message.subject or "Notification",
                body_text=message.body,
            )
            terminal, _ = _delivery_status_after_send("email", ok, detail)
            delivery.provider_name = provider_name
            delivery.last_error = None if ok else detail
            delivery.status = terminal
            session.flush()
            return DeliveryResult(success=ok, provider=provider_name, detail=detail)

        if channel == "sms":
            if not user.phone:
                delivery.status = "failed"
                delivery.last_error = "No phone on user profile"
                session.flush()
                return DeliveryResult(success=False, provider="none", detail="No phone on user profile")
            adapter = get_sms_adapter(settings)
            ok, provider_name, detail = adapter.send(to_number=user.phone, body=message.body)
            terminal, _ = _delivery_status_after_send("sms", ok, detail)
            delivery.provider_name = provider_name
            delivery.last_error = None if ok else detail
            delivery.status = terminal
            session.flush()
            return DeliveryResult(success=ok, provider=provider_name, detail=detail)

        return DeliveryResult(success=False, provider="none", detail="Unreachable")


def get_notification_provider() -> NotificationProvider:
    return CommunicationNotificationProvider()
