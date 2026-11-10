"""Business logic for F2.12 communication platform."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import audit
from app.audit.service import AuditOutcome, record_event
from app.communication import access as comm_access
from app.communication.providers.translation import get_translation_adapter
from app.communication.template_render import render_simple_template
from app.core.config import get_settings
from app.communication.schemas import (
    AnnouncementCreate,
    MessageSend,
    OperationalSend,
    PreferenceUpdate,
    ReminderCreate,
    TemplateCreate,
    TemplateUpdate,
    TranslationRequest,
    TranslationReview,
)
from app.db.models.communication import (
    CommunicationAnnouncement,
    CommunicationAnnouncementRecipient,
    CommunicationDelivery,
    CommunicationMessage,
    CommunicationMessageRecipient,
    CommunicationScheduledReminder,
    CommunicationTemplate,
    CommunicationTranslation,
    CommunicationUserPreference,
)
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.membership import OrganisationMembership
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.ops.notifications import CommunicationNotificationProvider, ReminderMessage
from app.tenancy.session_rls import apply_organisation_rls
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
PHONE_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _idempotency_key_parts(*parts: str) -> str:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()[:40]
    return h


def _require_messages_read(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.COMMUNICATION_MESSAGES_READ)


def _require_messages_send(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.COMMUNICATION_MESSAGES_SEND)


def dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    _require_messages_read(ctx)
    org_id = ctx.organisation_id
    user_id = ctx.user_id
    total_in_app = session.scalar(
        select(func.count())
        .select_from(CommunicationMessageRecipient)
        .where(
            CommunicationMessageRecipient.organisation_id == org_id,
            CommunicationMessageRecipient.recipient_user_id == user_id,
        )
    ) or 0
    unread = session.scalar(
        select(func.count())
        .select_from(CommunicationMessageRecipient)
        .where(
            CommunicationMessageRecipient.organisation_id == org_id,
            CommunicationMessageRecipient.recipient_user_id == user_id,
            CommunicationMessageRecipient.read_at.is_(None),
        )
    ) or 0

    def _count_statuses(statuses: tuple[str, ...]) -> int:
        q = select(func.count()).select_from(CommunicationDelivery).where(
            CommunicationDelivery.organisation_id == org_id,
            CommunicationDelivery.status.in_(statuses),
        )
        if not ctx.authorization.has_permission(Permission.COMMUNICATION_DELIVERIES_READ):
            q = q.where(CommunicationDelivery.recipient_user_id == user_id)
        return session.scalar(q) or 0

    queued = _count_statuses(("created", "queued", "retrying"))
    success = _count_statuses(("delivered", "provider_accepted"))
    failed = _count_statuses(("failed",))

    pending_rem = session.scalar(
        select(func.count())
        .select_from(CommunicationScheduledReminder)
        .where(
            CommunicationScheduledReminder.organisation_id == org_id,
            CommunicationScheduledReminder.status == "pending",
            CommunicationScheduledReminder.scheduled_at > _now(),
        )
    ) or 0
    overdue_rem = session.scalar(
        select(func.count())
        .select_from(CommunicationScheduledReminder)
        .where(
            CommunicationScheduledReminder.organisation_id == org_id,
            CommunicationScheduledReminder.status == "pending",
            CommunicationScheduledReminder.scheduled_at < _now(),
        )
    ) or 0

    active_ann = session.scalar(
        select(func.count())
        .select_from(CommunicationAnnouncement)
        .where(
            CommunicationAnnouncement.organisation_id == org_id,
            CommunicationAnnouncement.status == "published",
            or_(
                CommunicationAnnouncement.expires_at.is_(None),
                CommunicationAnnouncement.expires_at > _now(),
            ),
        )
    ) or 0

    pending_trn = session.scalar(
        select(func.count())
        .select_from(CommunicationTranslation)
        .where(
            CommunicationTranslation.organisation_id == org_id,
            CommunicationTranslation.status == "pending",
        )
    ) or 0

    return {
        "total_in_app_messages": int(total_in_app),
        "unread_messages": int(unread),
        "queued_deliveries": int(queued),
        "successful_deliveries": int(success),
        "failed_deliveries": int(failed),
        "pending_reminders": int(pending_rem),
        "overdue_reminders": int(overdue_rem),
        "active_emergency_announcements": int(active_ann),
        "pending_translation_reviews": int(pending_trn),
    }


def list_inbox(
    session: Session, ctx: OrganisationContext, *, page: int, page_size: int, q: str | None
) -> dict[str, Any]:
    _require_messages_read(ctx)
    base = (
        select(CommunicationMessageRecipient.id)
        .join(CommunicationMessage, CommunicationMessage.id == CommunicationMessageRecipient.message_id)
        .where(
            CommunicationMessageRecipient.organisation_id == ctx.organisation_id,
            CommunicationMessageRecipient.recipient_user_id == ctx.user_id,
        )
    )
    if q:
        base = base.where(
            or_(
                CommunicationMessage.subject.ilike(f"%{q}%"),
                CommunicationMessage.body.ilike(f"%{q}%"),
            )
        )
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        select(CommunicationMessageRecipient, CommunicationMessage)
        .join(CommunicationMessage, CommunicationMessage.id == CommunicationMessageRecipient.message_id)
        .where(
            CommunicationMessageRecipient.organisation_id == ctx.organisation_id,
            CommunicationMessageRecipient.recipient_user_id == ctx.user_id,
        )
        .order_by(CommunicationMessage.created_at.desc())
    )
    if q:
        stmt = stmt.where(
            or_(
                CommunicationMessage.subject.ilike(f"%{q}%"),
                CommunicationMessage.body.ilike(f"%{q}%"),
            )
        )
    rows = list(
        session.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    )
    items: list[dict[str, Any]] = []
    for rec, msg in rows:
        items.append(
            {
                "recipient_id": str(rec.id),
                "message_id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "subject": msg.subject,
                "body_preview": msg.body[:200],
                "created_at": msg.created_at.isoformat(),
                "read_at": rec.read_at.isoformat() if rec.read_at else None,
                "sender_user_id": str(msg.sender_user_id) if msg.sender_user_id else None,
                **message_resource_fields(msg),
            }
        )
    return {"items": items, "page": page, "page_size": page_size, "total": int(total)}


def message_resource_fields(message: Any) -> dict[str, str | None]:
    """Expose an existing message link so the staff app can open the record. No new data is created."""
    resource_id = getattr(message, "related_resource_id", None)
    resource_type = getattr(message, "related_resource_type", None)
    return {
        "related_resource_type": resource_type if isinstance(resource_type, str) else None,
        "related_resource_id": str(resource_id) if resource_id else None,
    }


def list_sent(
    session: Session, ctx: OrganisationContext, *, page: int, page_size: int
) -> dict[str, Any]:
    _require_messages_read(ctx)
    base = select(CommunicationMessage.id).where(
        CommunicationMessage.organisation_id == ctx.organisation_id,
        CommunicationMessage.sender_user_id == ctx.user_id,
    )
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        select(CommunicationMessage)
        .where(
            CommunicationMessage.organisation_id == ctx.organisation_id,
            CommunicationMessage.sender_user_id == ctx.user_id,
        )
        .order_by(CommunicationMessage.created_at.desc())
    )
    rows = list(session.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    items = [
        {
            "message_id": str(m.id),
            "conversation_id": str(m.conversation_id),
            "subject": m.subject,
            "body_preview": m.body[:200],
            "created_at": m.created_at.isoformat(),
        }
        for m in rows
    ]
    return {"items": items, "page": page, "page_size": page_size, "total": int(total)}


def get_message(session: Session, ctx: OrganisationContext, message_id: uuid.UUID) -> dict[str, Any]:
    _require_messages_read(ctx)
    msg = session.get(CommunicationMessage, message_id)
    if msg is None or msg.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    rec = session.scalar(
        select(CommunicationMessageRecipient).where(
            CommunicationMessageRecipient.message_id == message_id,
            CommunicationMessageRecipient.organisation_id == ctx.organisation_id,
            CommunicationMessageRecipient.recipient_user_id == ctx.user_id,
        )
    )
    is_sender = msg.sender_user_id == ctx.user_id
    if rec is None and not is_sender:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a party to this message")
    return {
        "message_id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "subject": msg.subject,
        "body": msg.body,
        "message_type": msg.message_type,
        "sender_user_id": str(msg.sender_user_id) if msg.sender_user_id else None,
        "created_at": msg.created_at.isoformat(),
        "read_at": rec.read_at.isoformat() if rec and rec.read_at else None,
        **message_resource_fields(msg),
    }


def mark_message_read(session: Session, ctx: OrganisationContext, message_id: uuid.UUID, read: bool) -> dict[str, Any]:
    _require_messages_read(ctx)
    rec = session.scalar(
        select(CommunicationMessageRecipient).where(
            CommunicationMessageRecipient.message_id == message_id,
            CommunicationMessageRecipient.organisation_id == ctx.organisation_id,
            CommunicationMessageRecipient.recipient_user_id == ctx.user_id,
        )
    )
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbox row not found")
    rec.read_at = _now() if read else None
    record_event(
        session,
        action=audit.events.COMMUNICATION_MESSAGE_READ,
        resource_type="communication_message",
        resource_id=message_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Message read state updated",
        metadata={"read": read},
    )
    return {"message_id": str(message_id), "read_at": rec.read_at.isoformat() if rec.read_at else None}


def conversation_messages(
    session: Session, ctx: OrganisationContext, conversation_id: uuid.UUID
) -> list[dict[str, Any]]:
    _require_messages_read(ctx)
    rows = list(
        session.scalars(
            select(CommunicationMessage)
            .where(
                CommunicationMessage.organisation_id == ctx.organisation_id,
                CommunicationMessage.conversation_id == conversation_id,
            )
            .order_by(CommunicationMessage.created_at.asc())
        ).all()
    )
    if not rows:
        return []
    allowed = False
    for m in rows:
        if m.sender_user_id == ctx.user_id:
            allowed = True
            break
        r = session.scalar(
            select(CommunicationMessageRecipient).where(
                CommunicationMessageRecipient.message_id == m.id,
                CommunicationMessageRecipient.recipient_user_id == ctx.user_id,
            )
        )
        if r is not None:
            allowed = True
            break
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conversation not accessible")
    return [
        {
            "message_id": str(m.id),
            "sender_user_id": str(m.sender_user_id) if m.sender_user_id else None,
            "body": m.body,
            "created_at": m.created_at.isoformat(),
        }
        for m in rows
    ]


def send_message(session: Session, ctx: OrganisationContext, body: MessageSend) -> dict[str, Any]:
    _require_messages_send(ctx)
    if len(body.body.encode("utf-8")) > 200_000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message body too large")
    comm_access.assert_can_message(
        session,
        ctx,
        recipient_user_id=body.recipient_user_id,
        conversation_tenant_id=body.conversation_tenant_id,
        conversation_property_id=body.conversation_property_id,
        conversation_maintenance_id=body.conversation_maintenance_id,
    )
    conv_id = body.conversation_id or uuid.uuid4()
    msg = CommunicationMessage(
        organisation_id=ctx.organisation_id,
        conversation_id=conv_id,
        sender_user_id=ctx.user_id,
        subject=body.subject,
        body=body.body,
        message_type="direct",
        related_resource_type=body.related_resource_type,
        related_resource_id=body.related_resource_id,
    )
    session.add(msg)
    session.flush()
    rec = CommunicationMessageRecipient(
        organisation_id=ctx.organisation_id,
        message_id=msg.id,
        recipient_user_id=body.recipient_user_id,
    )
    session.add(rec)
    record_event(
        session,
        action=audit.events.COMMUNICATION_MESSAGE_CREATE,
        resource_type="communication_message",
        resource_id=msg.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary="In-app message created",
        metadata={"recipient": str(body.recipient_user_id)},
    )
    return {"message_id": str(msg.id), "conversation_id": str(conv_id)}


def _get_template(session: Session, org_id: uuid.UUID, code: str) -> CommunicationTemplate:
    row = session.scalar(
        select(CommunicationTemplate).where(
            CommunicationTemplate.organisation_id == org_id,
            CommunicationTemplate.code == code,
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return row


def operational_send(session: Session, ctx: OrganisationContext, body: OperationalSend) -> dict[str, Any]:
    if body.channel == "email":
        require_permission(ctx.authorization, Permission.COMMUNICATION_CHANNEL_EMAIL_SEND)
    else:
        require_permission(ctx.authorization, Permission.COMMUNICATION_CHANNEL_SMS_SEND)
    comm_access.assert_recipient_in_same_org(session, ctx.organisation_id, body.recipient_user_id)

    text_body = body.body
    subject = body.subject or "Message"
    if body.template_code:
        tpl = _get_template(session, ctx.organisation_id, body.template_code)
        if tpl.channel != body.channel:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template channel mismatch")
        text_body = render_simple_template(tpl.body_template, body.template_variables, tpl.allowed_placeholders or [])
        if tpl.subject_template:
            subject = render_simple_template(tpl.subject_template, body.template_variables, tpl.allowed_placeholders or [])

    user = session.get(User, body.recipient_user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")

    prefs = session.scalar(
        select(CommunicationUserPreference).where(
            CommunicationUserPreference.organisation_id == ctx.organisation_id,
            CommunicationUserPreference.user_id == body.recipient_user_id,
        )
    )
    essential = body.essential_operational
    if body.channel == "sms":
        if not essential and prefs and (prefs.sms_suppressed or prefs.marketing_opt_out):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SMS suppressed for this recipient")
        if not user.phone or not PHONE_E164.match(user.phone):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient phone must be E.164 (+country...)")
    if body.channel == "email" and not essential and prefs and prefs.marketing_opt_out:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email opt-out applies")

    idem = _idempotency_key_parts(
        str(ctx.organisation_id),
        str(body.recipient_user_id),
        body.channel,
        subject,
        text_body[:2000],
    )
    prior = session.scalar(
        select(CommunicationDelivery).where(
            CommunicationDelivery.organisation_id == ctx.organisation_id,
            CommunicationDelivery.idempotency_key == idem,
        )
    )
    provider = CommunicationNotificationProvider()
    result = provider.send(
        session,
        ReminderMessage(
            organisation_id=str(ctx.organisation_id),
            recipient_user_id=str(body.recipient_user_id),
            subject=subject,
            body=text_body,
            channel=body.channel,
            target_type="operational",
            target_id=str(ctx.organisation_id),
            idempotency_key=idem,
            essential_operational=body.essential_operational,
        ),
    )
    delivery = session.scalar(
        select(CommunicationDelivery).where(
            CommunicationDelivery.organisation_id == ctx.organisation_id,
            CommunicationDelivery.idempotency_key == idem,
        )
    )
    if delivery is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Delivery row missing after dispatch")
    record_event(
        session,
        action=audit.events.COMMUNICATION_DELIVERY_DISPATCH,
        resource_type="communication_delivery",
        resource_id=delivery.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value if result.success else AuditOutcome.FAILURE.value,
        summary="Operational delivery attempted",
        metadata={"channel": body.channel, "provider": result.provider, "detail": result.detail},
    )
    return {
        "delivery_id": str(delivery.id),
        "status": delivery.status,
        "provider": result.provider,
        "detail": result.detail,
        "deduplicated": prior is not None and prior.status in {"delivered", "provider_accepted"},
    }


def list_deliveries(
    session: Session, ctx: OrganisationContext, *, page: int, page_size: int
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_DELIVERIES_READ)
    base = select(CommunicationDelivery.id).where(CommunicationDelivery.organisation_id == ctx.organisation_id)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        select(CommunicationDelivery)
        .where(CommunicationDelivery.organisation_id == ctx.organisation_id)
        .order_by(CommunicationDelivery.created_at.desc())
    )
    rows = list(session.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    items = [
        {
            "id": str(d.id),
            "channel": d.channel,
            "status": d.status,
            "recipient_user_id": str(d.recipient_user_id),
            "scheduled_at": d.scheduled_at.isoformat(),
            "attempt_count": d.attempt_count,
            "provider_name": d.provider_name,
            "last_error": d.last_error[:500] if d.last_error else None,
        }
        for d in rows
    ]
    return {"items": items, "page": page, "page_size": page_size, "total": int(total)}


def get_or_create_prefs(session: Session, ctx: OrganisationContext) -> CommunicationUserPreference:
    row = session.scalar(
        select(CommunicationUserPreference).where(
            CommunicationUserPreference.organisation_id == ctx.organisation_id,
            CommunicationUserPreference.user_id == ctx.user_id,
        )
    )
    if row is None:
        row = CommunicationUserPreference(organisation_id=ctx.organisation_id, user_id=ctx.user_id)
        session.add(row)
        session.flush()
    return row


def update_prefs(session: Session, ctx: OrganisationContext, body: PreferenceUpdate) -> dict[str, Any]:
    row = get_or_create_prefs(session, ctx)
    if body.allow_in_app is not None:
        row.allow_in_app = body.allow_in_app
    if body.allow_email is not None:
        row.allow_email = body.allow_email
    if body.allow_sms is not None:
        row.allow_sms = body.allow_sms
    if body.marketing_opt_out is not None:
        row.marketing_opt_out = body.marketing_opt_out
    if body.sms_suppressed is not None:
        row.sms_suppressed = body.sms_suppressed
    record_event(
        session,
        action=audit.events.COMMUNICATION_PREFERENCE_UPDATE,
        resource_type="communication_preference",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Communication preferences updated",
        metadata={k: getattr(row, k) for k in ("allow_in_app", "allow_email", "allow_sms", "marketing_opt_out", "sms_suppressed")},
    )
    return {
        "allow_in_app": row.allow_in_app,
        "allow_email": row.allow_email,
        "allow_sms": row.allow_sms,
        "marketing_opt_out": row.marketing_opt_out,
        "sms_suppressed": row.sms_suppressed,
    }


def create_reminder(session: Session, ctx: OrganisationContext, body: ReminderCreate) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_REMINDERS_MANAGE)
    comm_access.assert_recipient_in_same_org(session, ctx.organisation_id, body.recipient_user_id)
    idem = _idempotency_key_parts(
        str(ctx.organisation_id),
        body.reminder_kind,
        str(body.recipient_user_id),
        body.scheduled_at.isoformat(),
        str(body.resource_id or ""),
        body.channel,
    )
    exists = session.scalar(
        select(CommunicationScheduledReminder.id).where(
            CommunicationScheduledReminder.organisation_id == ctx.organisation_id,
            CommunicationScheduledReminder.idempotency_key == idem,
        )
    )
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate reminder schedule")

    row = CommunicationScheduledReminder(
        organisation_id=ctx.organisation_id,
        reminder_kind=body.reminder_kind,
        recipient_user_id=body.recipient_user_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        channel=body.channel,
        subject=body.subject,
        body=body.body,
        scheduled_at=body.scheduled_at,
        status="pending",
        idempotency_key=idem,
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit.events.COMMUNICATION_REMINDER_CREATE,
        resource_type="communication_scheduled_reminder",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Scheduled communication reminder created",
        metadata={"kind": body.reminder_kind, "channel": body.channel},
    )
    return {"id": str(row.id)}


def list_reminders(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_REMINDERS_MANAGE)
    rows = list(
        session.scalars(
            select(CommunicationScheduledReminder)
            .where(CommunicationScheduledReminder.organisation_id == ctx.organisation_id)
            .order_by(CommunicationScheduledReminder.scheduled_at.asc())
            .limit(200)
        ).all()
    )
    return [
        {
            "id": str(r.id),
            "reminder_kind": r.reminder_kind,
            "scheduled_at": r.scheduled_at.isoformat(),
            "status": r.status,
            "channel": r.channel,
        }
        for r in rows
    ]


def cancel_reminder(session: Session, ctx: OrganisationContext, reminder_id: uuid.UUID) -> None:
    require_permission(ctx.authorization, Permission.COMMUNICATION_REMINDERS_MANAGE)
    row = session.get(CommunicationScheduledReminder, reminder_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    row.status = "cancelled"
    record_event(
        session,
        action=audit.events.COMMUNICATION_REMINDER_CANCEL,
        resource_type="communication_scheduled_reminder",
        resource_id=reminder_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Reminder cancelled",
    )


def _next_ann_reference(session: Session, org_id: uuid.UUID) -> str:
    last = session.scalar(
        select(CommunicationAnnouncement.reference_number)
        .where(CommunicationAnnouncement.organisation_id == org_id)
        .order_by(CommunicationAnnouncement.created_at.desc())
        .limit(1)
    )
    if last is None:
        return "ANN-00001"
    try:
        num = int(str(last).split("-")[-1])
    except ValueError:
        num = session.scalar(
            select(func.count()).select_from(
                select(CommunicationAnnouncement.id).where(CommunicationAnnouncement.organisation_id == org_id).subquery()
            )
        ) or 0
    return f"ANN-{num + 1:05d}"


def _resolve_audience_user_ids(session: Session, org_id: uuid.UUID, audience: str, custom: list[uuid.UUID]) -> list[uuid.UUID]:
    q = select(OrganisationMembership.user_id).where(
        OrganisationMembership.organisation_id == org_id,
        OrganisationMembership.status == MembershipStatus.ACTIVE,
    )
    if audience == "organisation_all":
        rows = list(session.scalars(q).all())
        return list(rows)
    if audience == "staff_only":
        rows = list(
            session.scalars(
                q.where(
                    OrganisationMembership.role.in_(
                        (
                            HMoreRole.ORGANISATION_ADMIN,
                            HMoreRole.SUPPORT_WORKER,
                            HMoreRole.LANDLORD,
                            HMoreRole.MAINTENANCE_CONTRACTOR,
                        )
                    )
                )
            ).all()
        )
        return list(rows)
    if audience == "tenants_only":
        rows = list(session.scalars(q.where(OrganisationMembership.role == HMoreRole.TENANT)).all())
        return list(rows)
    if audience == "landlords_only":
        rows = list(session.scalars(q.where(OrganisationMembership.role == HMoreRole.LANDLORD)).all())
        return list(rows)
    if audience == "custom_users":
        out: list[uuid.UUID] = []
        for uid in custom:
            comm_access.assert_recipient_in_same_org(session, org_id, uid)
            out.append(uid)
        return out
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid audience")


def create_announcement(session: Session, ctx: OrganisationContext, body: AnnouncementCreate) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_ANNOUNCEMENTS_PUBLISH)
    if ctx.role not in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Organisation Admin or Super Admin may create emergency announcements",
        )
    channels = body.channels
    if not any(channels.get(k) for k in ("in_app", "email", "sms")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select at least one channel")
    ref = _next_ann_reference(session, ctx.organisation_id)
    custom_ids = list(body.custom_user_ids or [])
    if body.audience == "custom_users" and not custom_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="custom_user_ids required for custom audience")

    ann = CommunicationAnnouncement(
        organisation_id=ctx.organisation_id,
        reference_number=ref,
        title=body.title,
        body=body.body,
        priority=body.priority,
        audience=body.audience,
        audience_user_ids=custom_ids if body.audience == "custom_users" else None,
        channels=channels,
        status="draft",
        created_by_user_id=ctx.user_id,
        expires_at=body.expires_at,
    )
    session.add(ann)
    session.flush()

    if body.target_language:
        adapter = get_translation_adapter(get_settings())
        ok, provider, _msg, translated = adapter.translate(
            text=body.body,
            source_language="en",
            target_language=body.target_language,
        )
        tr = CommunicationTranslation(
            organisation_id=ctx.organisation_id,
            target_type="announcement",
            target_id=ann.id,
            target_field="body",
            source_language="en",
            target_language=body.target_language,
            original_text=body.body,
            translated_text=translated if ok else None,
            status=("pending" if body.require_translation_review else ("completed" if ok else "failed")),
            provider_name=provider,
        )
        session.add(tr)

    record_event(
        session,
        action=audit.events.COMMUNICATION_ANNOUNCEMENT_CREATE,
        resource_type="communication_announcement",
        resource_id=ann.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Announcement draft created",
    )
    return {"announcement_id": str(ann.id), "reference_number": ref}


def _announcement_requires_translation_review(session: Session, org_id: uuid.UUID, ann_id: uuid.UUID) -> bool:
    row = session.scalar(
        select(CommunicationTranslation).where(
            CommunicationTranslation.organisation_id == org_id,
            CommunicationTranslation.target_type == "announcement",
            CommunicationTranslation.target_id == ann_id,
            CommunicationTranslation.status == "pending",
        )
    )
    return row is not None


def publish_announcement(session: Session, ctx: OrganisationContext, announcement_id: uuid.UUID) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_ANNOUNCEMENTS_PUBLISH)
    if ctx.role not in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted to publish announcements")

    ann = session.get(CommunicationAnnouncement, announcement_id)
    if ann is None or ann.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    if ann.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Announcement is not in draft status")
    if _announcement_requires_translation_review(session, ctx.organisation_id, ann.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Translation review required before publish")

    custom = list(ann.audience_user_ids or []) if ann.audience == "custom_users" else []
    user_ids = _resolve_audience_user_ids(session, ctx.organisation_id, ann.audience, custom)
    user_ids = list(dict.fromkeys(user_ids))
    ann.status = "published"
    ann.published_at = _now()
    ann.published_by_user_id = ctx.user_id

    provider = CommunicationNotificationProvider()
    apply_organisation_rls(session, ctx.organisation_id)
    for uid in user_ids:
        session.merge(
            CommunicationAnnouncementRecipient(
                organisation_id=ctx.organisation_id,
                announcement_id=ann.id,
                user_id=uid,
            )
        )
        if ann.channels.get("in_app"):
            conv_id = ann.id
            msg = CommunicationMessage(
                organisation_id=ctx.organisation_id,
                conversation_id=conv_id,
                sender_user_id=None,
                subject=ann.title,
                body=ann.body,
                message_type="system",
                related_resource_type="announcement",
                related_resource_id=ann.id,
            )
            session.add(msg)
            session.flush()
            session.add(
                CommunicationMessageRecipient(
                    organisation_id=ctx.organisation_id,
                    message_id=msg.id,
                    recipient_user_id=uid,
                )
            )
        if ann.channels.get("email"):
            provider.send(
                session,
                ReminderMessage(
                    organisation_id=str(ctx.organisation_id),
                    recipient_user_id=str(uid),
                    subject=ann.title,
                    body=ann.body,
                    channel="email",
                    target_type="announcement",
                    target_id=str(ann.id),
                    idempotency_key=f"announcement:{ann.id}:email:{uid}",
                    essential_operational=True,
                ),
            )
        if ann.channels.get("sms"):
            provider.send(
                session,
                ReminderMessage(
                    organisation_id=str(ctx.organisation_id),
                    recipient_user_id=str(uid),
                    subject=ann.title,
                    body=ann.body[:600],
                    channel="sms",
                    target_type="announcement",
                    target_id=str(ann.id),
                    idempotency_key=f"announcement:{ann.id}:sms:{uid}",
                    essential_operational=True,
                ),
            )

    record_event(
        session,
        action=audit.events.COMMUNICATION_ANNOUNCEMENT_PUBLISH,
        resource_type="communication_announcement",
        resource_id=ann.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Announcement published",
        metadata={"audience": ann.audience, "recipient_count": len(user_ids)},
    )
    return {"announcement_id": str(ann.id), "status": ann.status}


def cancel_announcement(session: Session, ctx: OrganisationContext, announcement_id: uuid.UUID) -> None:
    require_permission(ctx.authorization, Permission.COMMUNICATION_ANNOUNCEMENTS_PUBLISH)
    if ctx.role not in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
    ann = session.get(CommunicationAnnouncement, announcement_id)
    if ann is None or ann.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    ann.status = "cancelled"
    record_event(
        session,
        action=audit.events.COMMUNICATION_ANNOUNCEMENT_CANCEL,
        resource_type="communication_announcement",
        resource_id=announcement_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Announcement cancelled",
    )


def list_announcements(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_ANNOUNCEMENTS_READ)
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN, HMoreRole.SUPPORT_WORKER}:
        rows = list(
            session.scalars(
                select(CommunicationAnnouncement)
                .where(
                    CommunicationAnnouncement.organisation_id == ctx.organisation_id,
                    CommunicationAnnouncement.status == "published",
                )
                .order_by(CommunicationAnnouncement.published_at.desc().nulls_last())
                .limit(100)
            ).all()
        )
    else:
        rows = list(
            session.scalars(
                select(CommunicationAnnouncement)
                .join(
                    CommunicationAnnouncementRecipient,
                    CommunicationAnnouncementRecipient.announcement_id == CommunicationAnnouncement.id,
                )
                .where(
                    CommunicationAnnouncement.organisation_id == ctx.organisation_id,
                    CommunicationAnnouncement.status == "published",
                    CommunicationAnnouncementRecipient.user_id == ctx.user_id,
                )
                .order_by(CommunicationAnnouncement.published_at.desc().nulls_last())
                .limit(100)
            ).all()
        )
    return [
        {
            "id": str(a.id),
            "reference_number": a.reference_number,
            "title": a.title,
            "priority": a.priority,
            "published_at": a.published_at.isoformat() if a.published_at else None,
        }
        for a in rows
    ]


def get_announcement(session: Session, ctx: OrganisationContext, announcement_id: uuid.UUID) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_ANNOUNCEMENTS_READ)
    ann = session.get(CommunicationAnnouncement, announcement_id)
    if ann is None or ann.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    if ctx.role not in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN, HMoreRole.SUPPORT_WORKER}:
        rec = session.scalar(
            select(CommunicationAnnouncementRecipient).where(
                CommunicationAnnouncementRecipient.announcement_id == announcement_id,
                CommunicationAnnouncementRecipient.user_id == ctx.user_id,
            )
        )
        if rec is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Announcement not visible")
    return {
        "id": str(ann.id),
        "reference_number": ann.reference_number,
        "title": ann.title,
        "body": ann.body,
        "priority": ann.priority,
        "status": ann.status,
        "published_at": ann.published_at.isoformat() if ann.published_at else None,
    }


def request_translation(
    session: Session,
    ctx: OrganisationContext,
    *,
    target_type: str,
    target_id: uuid.UUID,
    body: TranslationRequest,
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_TRANSLATIONS_MANAGE)
    text: str | None = None
    if target_type == "announcement":
        ann = session.get(CommunicationAnnouncement, target_id)
        if ann is None or ann.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
        text = ann.title if body.target_field == "title" else ann.body
    elif target_type == "message":
        msg = session.get(CommunicationMessage, target_id)
        if msg is None or msg.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        text = msg.subject if body.target_field == "title" else msg.body
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported target_type")

    adapter = get_translation_adapter(get_settings())
    ok, provider, _msg, translated = adapter.translate(
        text=text or "",
        source_language=body.source_language,
        target_language=body.target_language,
    )
    row = CommunicationTranslation(
        organisation_id=ctx.organisation_id,
        target_type=target_type,
        target_id=target_id,
        target_field=body.target_field,
        source_language=body.source_language,
        target_language=body.target_language,
        original_text=text or "",
        translated_text=translated if ok else None,
        status="completed" if ok else "failed",
        provider_name=provider,
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit.events.COMMUNICATION_TRANSLATION_REQUEST,
        resource_type="communication_translation",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Translation requested",
        metadata={"target_type": target_type, "target_id": str(target_id)},
    )
    return {"translation_id": str(row.id), "status": row.status}


def review_translation(
    session: Session, ctx: OrganisationContext, translation_id: uuid.UUID, body: TranslationReview
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_TRANSLATIONS_MANAGE)
    row = session.get(CommunicationTranslation, translation_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Translation not found")
    row.translated_text = body.translated_text
    row.status = "reviewed"
    row.reviewed_at = _now()
    row.reviewed_by_user_id = ctx.user_id
    record_event(
        session,
        action=audit.events.COMMUNICATION_TRANSLATION_REVIEW,
        resource_type="communication_translation",
        resource_id=translation_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Translation reviewed",
    )
    return {"translation_id": str(row.id), "status": row.status}


def list_templates(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_TEMPLATES_MANAGE)
    rows = list(
        session.scalars(
            select(CommunicationTemplate)
            .where(CommunicationTemplate.organisation_id == ctx.organisation_id)
            .order_by(CommunicationTemplate.code.asc())
        ).all()
    )
    return [{"id": str(t.id), "code": t.code, "title": t.title, "channel": t.channel} for t in rows]


def create_template(session: Session, ctx: OrganisationContext, body: TemplateCreate) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_TEMPLATES_MANAGE)
    tpl = CommunicationTemplate(
        organisation_id=ctx.organisation_id,
        code=body.code,
        title=body.title,
        channel=body.channel,
        subject_template=body.subject_template,
        body_template=body.body_template,
        allowed_placeholders=body.allowed_placeholders,
    )
    session.add(tpl)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Template code already exists") from exc
    record_event(
        session,
        action=audit.events.COMMUNICATION_TEMPLATE_UPDATE,
        resource_type="communication_template",
        resource_id=tpl.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Communication template created",
    )
    return {"template_id": str(tpl.id)}


def patch_template(
    session: Session, ctx: OrganisationContext, template_id: uuid.UUID, body: TemplateUpdate
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.COMMUNICATION_TEMPLATES_MANAGE)
    tpl = session.get(CommunicationTemplate, template_id)
    if tpl is None or tpl.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    if body.title is not None:
        tpl.title = body.title
    if body.subject_template is not None:
        tpl.subject_template = body.subject_template
    if body.body_template is not None:
        tpl.body_template = body.body_template
    if body.allowed_placeholders is not None:
        tpl.allowed_placeholders = body.allowed_placeholders
    record_event(
        session,
        action=audit.events.COMMUNICATION_TEMPLATE_UPDATE,
        resource_type="communication_template",
        resource_id=template_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Communication template updated",
    )
    return {"template_id": str(tpl.id)}
