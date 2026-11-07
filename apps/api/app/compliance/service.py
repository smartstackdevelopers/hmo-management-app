"""F2.3 training records and safeguarding reminder services."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.compliance import access
from app.compliance.schemas import (
    SafeguardingCreate,
    SafeguardingUpdate,
    TrainingCreate,
    TrainingUpdate,
)
from app.core.config import get_settings
from app.db.models.compliance import SafeguardingReminder, StaffTrainingRecord
from app.db.models.enums import HMoreRole
from app.db.models.scheduling import ReminderRecord
from app.records.pagination import offset_limit
from app.tenancy.context import OrganisationContext

SAFEGUARDING_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"sent", "acknowledged", "completed", "cancelled", "overdue"}),
    "sent": frozenset({"acknowledged", "completed", "cancelled", "overdue"}),
    "acknowledged": frozenset({"completed", "cancelled", "overdue"}),
    "overdue": frozenset({"acknowledged", "completed", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


def _audit(
    session: Session,
    ctx: OrganisationContext,
    *,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    record_event(
        session,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary=summary,
        metadata=metadata or {},
    )


def effective_training_status(row: StaffTrainingRecord, *, soon_days: int | None = None) -> str:
    """Derive display status from stored status + expiry dates."""
    settings = get_settings()
    lead = soon_days if soon_days is not None else settings.reminder_training_expiry_lead_days
    if row.status == "exempt":
        return "exempt"
    if row.status in {"not_started", "in_progress"}:
        return row.status
    if row.status == "completed":
        if row.expiry_date is None:
            return "completed"
        today = _today()
        if row.expiry_date < today:
            return "expired"
        if row.expiry_date <= today + timedelta(days=lead):
            return "expiring_soon"
        return "completed"
    return row.status


def training_out_dict(row: StaffTrainingRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "organisation_id": row.organisation_id,
        "staff_user_id": row.staff_user_id,
        "created_by_user_id": row.created_by_user_id,
        "title": row.title,
        "category": row.category,
        "provider": row.provider,
        "completion_date": row.completion_date,
        "expiry_date": row.expiry_date,
        "required_by_date": row.required_by_date,
        "evidence_file_id": row.evidence_file_id,
        "status": row.status,
        "effective_status": effective_training_status(row),
        "notes": row.notes,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _upsert_delivery_reminder(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    reminder_kind: str,
    recipient_user_id: uuid.UUID,
    scheduled_for: datetime,
    summary: str,
) -> ReminderRecord | None:
    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)
    existing = session.scalar(
        select(ReminderRecord).where(
            ReminderRecord.organisation_id == organisation_id,
            ReminderRecord.resource_type == resource_type,
            ReminderRecord.resource_id == resource_id,
            ReminderRecord.reminder_kind == reminder_kind,
            ReminderRecord.scheduled_for == scheduled_for,
        )
    )
    if existing is not None:
        return existing
    row = ReminderRecord(
        organisation_id=organisation_id,
        resource_type=resource_type,
        resource_id=resource_id,
        reminder_kind=reminder_kind,
        recipient_user_id=recipient_user_id,
        scheduled_for=scheduled_for,
        status="pending",
        channel="in_app",
        payload_summary=summary[:255],
    )
    session.add(row)
    session.flush()
    return row


def _cancel_pending_delivery(
    session: Session, organisation_id: uuid.UUID, resource_type: str, resource_id: uuid.UUID
) -> None:
    rows = session.scalars(
        select(ReminderRecord).where(
            ReminderRecord.organisation_id == organisation_id,
            ReminderRecord.resource_type == resource_type,
            ReminderRecord.resource_id == resource_id,
            ReminderRecord.status == "pending",
        )
    ).all()
    for row in rows:
        row.status = "cancelled"


def schedule_training_reminders(
    session: Session, ctx: OrganisationContext, row: StaffTrainingRecord
) -> None:
    settings = get_settings()
    _cancel_pending_delivery(session, ctx.organisation_id, "staff_training", row.id)
    if row.status == "exempt":
        return
    if row.status in {"not_started", "in_progress"} and row.required_by_date is not None:
        due_dt = datetime.combine(row.required_by_date, datetime.min.time(), tzinfo=timezone.utc)
        _upsert_delivery_reminder(
            session,
            organisation_id=ctx.organisation_id,
            resource_type="staff_training",
            resource_id=row.id,
            reminder_kind="training_incomplete_due",
            recipient_user_id=row.staff_user_id,
            scheduled_for=due_dt + timedelta(minutes=1),
            summary=f"Incomplete training due: {row.title}",
        )
    if row.status == "completed" and row.expiry_date is not None:
        lead = timedelta(days=settings.reminder_training_expiry_lead_days)
        expiry_dt = datetime.combine(row.expiry_date, datetime.min.time(), tzinfo=timezone.utc)
        soon_at = expiry_dt - lead
        if soon_at > _now():
            _upsert_delivery_reminder(
                session,
                organisation_id=ctx.organisation_id,
                resource_type="staff_training",
                resource_id=row.id,
                reminder_kind="training_expiring_soon",
                recipient_user_id=row.staff_user_id,
                scheduled_for=soon_at,
                summary=f"Training expiring soon: {row.title}",
            )
        _upsert_delivery_reminder(
            session,
            organisation_id=ctx.organisation_id,
            resource_type="staff_training",
            resource_id=row.id,
            reminder_kind="training_expired",
            recipient_user_id=row.staff_user_id,
            scheduled_for=expiry_dt + timedelta(minutes=1),
            summary=f"Training expired: {row.title}",
        )
    _audit(
        session,
        ctx,
        action=audit_events.REMINDER_SCHEDULE,
        resource_type="staff_training_record",
        resource_id=row.id,
        summary="Training reminders scheduled",
        metadata={"title": row.title},
    )


def schedule_safeguarding_delivery(
    session: Session, ctx: OrganisationContext, row: SafeguardingReminder
) -> None:
    settings = get_settings()
    _cancel_pending_delivery(session, ctx.organisation_id, "safeguarding_reminder", row.id)
    if row.status in {"completed", "cancelled"}:
        return
    lead = timedelta(minutes=settings.reminder_safeguarding_lead_minutes)
    # Privacy: never put description in notification payload.
    summary = f"Safeguarding action due: {row.title}"
    _upsert_delivery_reminder(
        session,
        organisation_id=ctx.organisation_id,
        resource_type="safeguarding_reminder",
        resource_id=row.id,
        reminder_kind="safeguarding_upcoming",
        recipient_user_id=row.assigned_user_id,
        scheduled_for=row.due_at - lead,
        summary=summary,
    )
    _upsert_delivery_reminder(
        session,
        organisation_id=ctx.organisation_id,
        resource_type="safeguarding_reminder",
        resource_id=row.id,
        reminder_kind="safeguarding_overdue",
        recipient_user_id=row.assigned_user_id,
        scheduled_for=row.due_at + timedelta(minutes=1),
        summary=f"Safeguarding action overdue: {row.title}",
    )
    _audit(
        session,
        ctx,
        action=audit_events.REMINDER_SCHEDULE,
        resource_type="safeguarding_reminder",
        resource_id=row.id,
        summary="Safeguarding delivery reminders scheduled",
        metadata={"category": row.category},
    )


def create_training(
    session: Session, ctx: OrganisationContext, data: TrainingCreate
) -> StaffTrainingRecord:
    access.require_training_manage(ctx)
    access.assert_active_org_member(
        session, organisation_id=ctx.organisation_id, user_id=data.staff_user_id
    )
    row = StaffTrainingRecord(
        organisation_id=ctx.organisation_id,
        staff_user_id=data.staff_user_id,
        created_by_user_id=ctx.user_id,
        title=data.title,
        category=data.category,
        provider=data.provider,
        completion_date=data.completion_date,
        expiry_date=data.expiry_date,
        required_by_date=data.required_by_date,
        evidence_file_id=data.evidence_file_id,
        status=data.status,
        notes=data.notes,
    )
    session.add(row)
    session.flush()
    schedule_training_reminders(session, ctx, row)
    _audit(
        session,
        ctx,
        action=audit_events.TRAINING_CREATE,
        resource_type="staff_training_record",
        resource_id=row.id,
        summary="Training record created",
        metadata={"category": row.category, "status": row.status},
    )
    if row.status == "completed":
        _audit(
            session,
            ctx,
            action=audit_events.TRAINING_COMPLETE,
            resource_type="staff_training_record",
            resource_id=row.id,
            summary="Training marked completed",
        )
    return row


def get_training(
    session: Session, ctx: OrganisationContext, training_id: uuid.UUID
) -> StaffTrainingRecord:
    access.require_training_read(ctx)
    row = session.get(StaffTrainingRecord, training_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training record not found")
    if ctx.role == HMoreRole.SUPPORT_WORKER and row.staff_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return row


def list_training(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    staff_user_id: uuid.UUID | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    expiring_only: bool = False,
    expired_only: bool = False,
) -> tuple[list[StaffTrainingRecord], int]:
    access.require_training_read(ctx)
    stmt = select(StaffTrainingRecord).where(
        StaffTrainingRecord.organisation_id == ctx.organisation_id
    )
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(StaffTrainingRecord.staff_user_id == ctx.user_id)
    elif staff_user_id is not None:
        stmt = stmt.where(StaffTrainingRecord.staff_user_id == staff_user_id)
    if category:
        stmt = stmt.where(StaffTrainingRecord.category == category)
    if status_filter:
        stmt = stmt.where(StaffTrainingRecord.status == status_filter)
    settings = get_settings()
    today = _today()
    soon = today + timedelta(days=settings.reminder_training_expiry_lead_days)
    if expired_only:
        stmt = stmt.where(
            StaffTrainingRecord.status == "completed",
            StaffTrainingRecord.expiry_date.is_not(None),
            StaffTrainingRecord.expiry_date < today,
        )
    elif expiring_only:
        stmt = stmt.where(
            StaffTrainingRecord.status == "completed",
            StaffTrainingRecord.expiry_date.is_not(None),
            StaffTrainingRecord.expiry_date >= today,
            StaffTrainingRecord.expiry_date <= soon,
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(
            stmt.order_by(StaffTrainingRecord.expiry_date.asc().nulls_last()).offset(offset).limit(limit)
        ).all()
    )
    return rows, total


def update_training(
    session: Session,
    ctx: OrganisationContext,
    training_id: uuid.UUID,
    data: TrainingUpdate,
) -> StaffTrainingRecord:
    access.require_training_manage(ctx)
    row = session.get(StaffTrainingRecord, training_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training record not found")
    payload = data.model_dump(exclude_unset=True)
    prev_status = row.status
    for key, value in payload.items():
        setattr(row, key, value)
    completion = row.completion_date
    expiry = row.expiry_date
    if completion is not None and expiry is not None and expiry < completion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expiry_date must be on or after completion_date",
        )
    if row.status == "completed" and row.completion_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="completion_date is required when status is completed",
        )
    # Cannot mark expired training as completed without a new completion cycle —
    # callers must set a fresh completion_date / expiry when renewing.
    session.flush()
    schedule_training_reminders(session, ctx, row)
    _audit(
        session,
        ctx,
        action=audit_events.TRAINING_UPDATE,
        resource_type="staff_training_record",
        resource_id=row.id,
        summary="Training record updated",
        metadata={"status": row.status},
    )
    if prev_status != "completed" and row.status == "completed":
        _audit(
            session,
            ctx,
            action=audit_events.TRAINING_COMPLETE,
            resource_type="staff_training_record",
            resource_id=row.id,
            summary="Training marked completed",
        )
    return row


def create_safeguarding(
    session: Session, ctx: OrganisationContext, data: SafeguardingCreate
) -> SafeguardingReminder:
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        access.require_safeguarding_access(ctx)
    else:
        access.require_safeguarding_manage(ctx)
    access.assert_safeguarding_assignee_scope(
        session,
        ctx,
        assigned_user_id=data.assigned_user_id,
        tenant_id=data.tenant_id,
    )
    if data.related_staff_user_id is not None:
        access.assert_active_org_member(
            session, organisation_id=ctx.organisation_id, user_id=data.related_staff_user_id
        )
    row = SafeguardingReminder(
        organisation_id=ctx.organisation_id,
        related_staff_user_id=data.related_staff_user_id,
        tenant_id=data.tenant_id,
        assigned_user_id=data.assigned_user_id,
        created_by_user_id=ctx.user_id,
        category=data.category,
        title=data.title,
        description=data.description,
        due_at=data.due_at if data.due_at.tzinfo else data.due_at.replace(tzinfo=timezone.utc),
        priority=data.priority,
        status="pending",
    )
    session.add(row)
    session.flush()
    schedule_safeguarding_delivery(session, ctx, row)
    _audit(
        session,
        ctx,
        action=audit_events.SAFEGUARDING_REMINDER_CREATE,
        resource_type="safeguarding_reminder",
        resource_id=row.id,
        summary="Safeguarding reminder created",
        metadata={"category": row.category, "priority": row.priority},
    )
    return row


def get_safeguarding(
    session: Session, ctx: OrganisationContext, reminder_id: uuid.UUID
) -> SafeguardingReminder:
    access.require_safeguarding_access(ctx)
    row = session.get(SafeguardingReminder, reminder_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    if ctx.role == HMoreRole.SUPPORT_WORKER and row.assigned_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return row


def list_safeguarding(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    status_filter: str | None = None,
    overdue_only: bool = False,
    assigned_user_id: uuid.UUID | None = None,
) -> tuple[list[SafeguardingReminder], int]:
    access.require_safeguarding_access(ctx)
    stmt = select(SafeguardingReminder).where(
        SafeguardingReminder.organisation_id == ctx.organisation_id
    )
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(SafeguardingReminder.assigned_user_id == ctx.user_id)
    elif assigned_user_id is not None:
        stmt = stmt.where(SafeguardingReminder.assigned_user_id == assigned_user_id)
    if status_filter:
        stmt = stmt.where(SafeguardingReminder.status == status_filter)
    if overdue_only:
        stmt = stmt.where(
            SafeguardingReminder.due_at < _now(),
            SafeguardingReminder.status.in_(("pending", "sent", "acknowledged", "overdue")),
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(
            stmt.order_by(SafeguardingReminder.due_at.asc()).offset(offset).limit(limit)
        ).all()
    )
    return rows, total


def update_safeguarding(
    session: Session,
    ctx: OrganisationContext,
    reminder_id: uuid.UUID,
    data: SafeguardingUpdate,
) -> SafeguardingReminder:
    row = get_safeguarding(session, ctx, reminder_id)
    payload = data.model_dump(exclude_unset=True)
    if "assigned_user_id" in payload or "tenant_id" in payload:
        if ctx.role != HMoreRole.ORGANISATION_ADMIN and ctx.role != HMoreRole.SUPER_ADMIN:
            if "assigned_user_id" in payload and payload["assigned_user_id"] != ctx.user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        assignee = payload.get("assigned_user_id", row.assigned_user_id)
        tenant = payload.get("tenant_id", row.tenant_id)
        access.assert_safeguarding_assignee_scope(
            session, ctx, assigned_user_id=assignee, tenant_id=tenant
        )
        if "assigned_user_id" in payload and payload["assigned_user_id"] != row.assigned_user_id:
            _audit(
                session,
                ctx,
                action=audit_events.SAFEGUARDING_REMINDER_ASSIGN,
                resource_type="safeguarding_reminder",
                resource_id=row.id,
                summary="Safeguarding reminder reassigned",
            )
    if "status" in payload:
        target = payload["status"]
        allowed = SAFEGUARDING_TRANSITIONS.get(row.status, frozenset())
        if target != row.status and target not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition safeguarding reminder from {row.status} to {target}",
            )
        if target == "acknowledged" and row.acknowledged_at is None:
            row.acknowledged_at = _now()
            _audit(
                session,
                ctx,
                action=audit_events.SAFEGUARDING_REMINDER_ACKNOWLEDGE,
                resource_type="safeguarding_reminder",
                resource_id=row.id,
                summary="Safeguarding reminder acknowledged",
            )
        if target == "completed":
            row.completed_at = _now()
            _audit(
                session,
                ctx,
                action=audit_events.SAFEGUARDING_REMINDER_COMPLETE,
                resource_type="safeguarding_reminder",
                resource_id=row.id,
                summary="Safeguarding reminder completed",
            )
        if target == "cancelled":
            _audit(
                session,
                ctx,
                action=audit_events.SAFEGUARDING_REMINDER_CANCEL,
                resource_type="safeguarding_reminder",
                resource_id=row.id,
                summary="Safeguarding reminder cancelled",
            )
    for key, value in payload.items():
        setattr(row, key, value)
    if "due_at" in payload and row.due_at.tzinfo is None:
        row.due_at = row.due_at.replace(tzinfo=timezone.utc)
    session.flush()
    schedule_safeguarding_delivery(session, ctx, row)
    return row


def acknowledge_safeguarding(
    session: Session, ctx: OrganisationContext, reminder_id: uuid.UUID
) -> SafeguardingReminder:
    return update_safeguarding(
        session, ctx, reminder_id, SafeguardingUpdate(status="acknowledged")
    )


def complete_safeguarding(
    session: Session, ctx: OrganisationContext, reminder_id: uuid.UUID
) -> SafeguardingReminder:
    return update_safeguarding(session, ctx, reminder_id, SafeguardingUpdate(status="completed"))


def cancel_safeguarding(
    session: Session, ctx: OrganisationContext, reminder_id: uuid.UUID
) -> SafeguardingReminder:
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        # SW may cancel own assigned pending items
        access.require_safeguarding_access(ctx)
    else:
        access.require_safeguarding_manage(ctx)
    return update_safeguarding(session, ctx, reminder_id, SafeguardingUpdate(status="cancelled"))
