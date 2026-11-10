"""Create queued push deliveries and hand them to Expo from the worker.

Push copy is a fixed title and body. Message text, incident narrative, and
medical detail are never copied into the provider payload.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models.communication import CommunicationDelivery, CommunicationMessage, CommunicationUserPreference
from app.db.models.push_devices import PushDeviceToken
from app.push.expo_client import PUSH_BODY, PUSH_TITLE, send_expo_push
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

logger = logging.getLogger("hmore.push.delivery")

_TERMINAL = frozenset({"sent", "failed", "cancelled"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _allows_push(session: Session, organisation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    prefs = session.scalar(
        select(CommunicationUserPreference).where(
            CommunicationUserPreference.organisation_id == organisation_id,
            CommunicationUserPreference.user_id == user_id,
        )
    )
    if prefs is None:
        return True
    return bool(prefs.allow_push)


def _active_devices(session: Session, organisation_id: uuid.UUID, user_id: uuid.UUID) -> list[PushDeviceToken]:
    return list(
        session.scalars(
            select(PushDeviceToken).where(
                PushDeviceToken.organisation_id == organisation_id,
                PushDeviceToken.user_id == user_id,
                PushDeviceToken.is_active.is_(True),
            )
        ).all()
    )


def _idempotency(base: str, device_id: uuid.UUID) -> str:
    raw = f"push:{base}:{device_id}"
    if len(raw) <= 128:
        return raw
    import hashlib

    digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f"push:{digest}:{device_id}"


def _schedule(delivery_id: uuid.UUID) -> None:
    try:
        from app.workers.tasks import dispatch_push_delivery_task

        dispatch_push_delivery_task.delay(str(delivery_id))
    except Exception:
        logger.info("push_delivery_left_queued id=%s", delivery_id)


def enqueue_push_for_target(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID,
    idempotency_base: str,
) -> list[uuid.UUID]:
    """Queue one push delivery per active device. Returns delivery ids. Does not call Expo."""
    if not _allows_push(session, organisation_id, recipient_user_id):
        return []
    devices = _active_devices(session, organisation_id, recipient_user_id)
    created: list[uuid.UUID] = []
    for device in devices:
        key = _idempotency(idempotency_base, device.id)
        existing = session.scalar(
            select(CommunicationDelivery.id).where(
                CommunicationDelivery.organisation_id == organisation_id,
                CommunicationDelivery.idempotency_key == key,
            )
        )
        if existing is not None:
            continue
        delivery = CommunicationDelivery(
            id=uuid.uuid4(),
            organisation_id=organisation_id,
            target_type=target_type[:32],
            target_id=target_id,
            recipient_user_id=recipient_user_id,
            channel="push",
            status="queued",
            subject=PUSH_TITLE,
            body=PUSH_BODY,
            scheduled_at=_now(),
            attempt_count=0,
            idempotency_key=key,
        )
        session.add(delivery)
        session.flush()
        created.append(delivery.id)
        _schedule(delivery.id)
    return created


def enqueue_push_for_message(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
    message_id: uuid.UUID,
) -> list[uuid.UUID]:
    return enqueue_push_for_target(
        session,
        organisation_id=organisation_id,
        recipient_user_id=recipient_user_id,
        target_type="communication_message",
        target_id=message_id,
        idempotency_base=f"message:{message_id}",
    )


def enqueue_push_for_announcement(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
    announcement_id: uuid.UUID,
) -> list[uuid.UUID]:
    return enqueue_push_for_target(
        session,
        organisation_id=organisation_id,
        recipient_user_id=recipient_user_id,
        target_type="announcement",
        target_id=announcement_id,
        idempotency_base=f"announcement:{announcement_id}",
    )


def _device_id_from_key(idempotency_key: str) -> uuid.UUID | None:
    part = (idempotency_key or "").rsplit(":", 1)[-1]
    try:
        return uuid.UUID(part)
    except ValueError:
        return None


def _data_for_delivery(session: Session, delivery: CommunicationDelivery) -> dict[str, str]:
    if delivery.target_type == "communication_message":
        message = session.get(CommunicationMessage, delivery.target_id)
        if message is None:
            return {
                "message_id": str(delivery.target_id),
                "related_resource_type": "",
                "related_resource_id": "",
            }
        return {
            "message_id": str(message.id),
            "related_resource_type": (message.related_resource_type or "")[:64],
            "related_resource_id": str(message.related_resource_id) if message.related_resource_id else "",
        }
    if delivery.target_type == "announcement":
        return {
            "message_id": "",
            "related_resource_type": "announcement",
            "related_resource_id": str(delivery.target_id),
        }
    opaque = {"operational", "reminder_record", "communication_scheduled_reminder"}
    if delivery.target_type in opaque:
        return {"message_id": "", "related_resource_type": "", "related_resource_id": ""}
    return {
        "message_id": "",
        "related_resource_type": (delivery.target_type or "")[:64],
        "related_resource_id": str(delivery.target_id),
    }


def deliver_push(
    session: Session,
    delivery: CommunicationDelivery,
    device: PushDeviceToken | None,
    *,
    settings: Settings,
    data: dict[str, str],
    http_post: Any = None,
) -> dict[str, Any]:
    """Move one push delivery queued → sending → sent or failed.

    ``sent`` is set only when Expo returns a ticket with status ok and an id.
    Log mode records ``provider_not_configured`` and does not mark the delivery sent.
    """
    if delivery.status in _TERMINAL:
        return {"delivery_id": str(delivery.id), "status": delivery.status, "noop": True}
    if delivery.channel != "push":
        return {"delivery_id": str(delivery.id), "status": delivery.status, "noop": True}

    delivery.status = "sending"
    delivery.attempt_count = int(delivery.attempt_count or 0) + 1
    delivery.last_attempt_at = _now()

    if device is None or not device.is_active or not device.expo_push_token:
        delivery.status = "failed"
        delivery.provider_name = "push"
        delivery.last_error = "device_inactive"
        session.flush()
        return {"delivery_id": str(delivery.id), "status": "failed", "noop": False}

    outcome = send_expo_push(
        settings=settings,
        to_token=device.expo_push_token,
        data=data,
        http_post=http_post,
    )
    delivery.provider_name = outcome.provider
    if outcome.sent and outcome.ticket_id:
        delivery.status = "sent"
        delivery.provider_message_id = outcome.ticket_id
        delivery.last_error = None
    else:
        delivery.status = "failed"
        delivery.provider_message_id = None
        delivery.last_error = outcome.error or "push_failed"
        if outcome.deactivate_device:
            device.is_active = False
            device.disabled_reason = "DeviceNotRegistered"
    session.flush()
    return {
        "delivery_id": str(delivery.id),
        "status": delivery.status,
        "noop": False,
        "provider": delivery.provider_name,
    }


def dispatch_loaded_delivery(
    session: Session,
    delivery: CommunicationDelivery,
    *,
    settings: Settings | None = None,
    http_post: Any = None,
) -> dict[str, Any]:
    if delivery.status in _TERMINAL:
        return {"delivery_id": str(delivery.id), "status": delivery.status, "noop": True}
    if delivery.status not in {"queued", "sending"} or delivery.channel != "push":
        return {"delivery_id": str(delivery.id), "status": delivery.status, "noop": True}
    device_id = _device_id_from_key(delivery.idempotency_key)
    device = session.get(PushDeviceToken, device_id) if device_id is not None else None
    data = _data_for_delivery(session, delivery)
    active = get_settings() if settings is None else settings
    return deliver_push(session, delivery, device, settings=active, data=data, http_post=http_post)


def dispatch_delivery_by_id(
    session: Session,
    delivery_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    http_post: Any = None,
) -> dict[str, Any]:
    apply_platform_rls_bypass(session)
    delivery = session.get(CommunicationDelivery, delivery_id)
    if delivery is None:
        return {"missing": True}
    apply_organisation_rls(session, delivery.organisation_id)
    return dispatch_loaded_delivery(session, delivery, settings=settings, http_post=http_post)


def dispatch_pending(
    session: Session,
    *,
    limit: int = 50,
    settings: Settings | None = None,
    http_post: Any = None,
) -> dict[str, int]:
    apply_platform_rls_bypass(session)
    rows = list(
        session.scalars(
            select(CommunicationDelivery)
            .where(
                CommunicationDelivery.channel == "push",
                CommunicationDelivery.status == "queued",
            )
            .order_by(CommunicationDelivery.scheduled_at.asc())
            .limit(limit)
        ).all()
    )
    counts = {"processed": 0, "sent": 0, "failed": 0, "noop": 0}
    for delivery in rows:
        apply_organisation_rls(session, delivery.organisation_id)
        result = dispatch_loaded_delivery(session, delivery, settings=settings, http_post=http_post)
        counts["processed"] += 1
        status_name = str(result.get("status") or "")
        if result.get("noop"):
            counts["noop"] += 1
        elif status_name == "sent":
            counts["sent"] += 1
        elif status_name == "failed":
            counts["failed"] += 1
    return counts
