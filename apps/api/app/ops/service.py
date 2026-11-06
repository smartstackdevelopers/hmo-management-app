"""F2.2 rota, visits, tasks, and reminder scheduling services."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import get_settings
from app.db.models.enums import HMoreRole
from app.db.models.scheduling import OperationalTask, ReminderRecord, StaffShift, TenantVisit
from app.db.models.support_ops import DailyLog
from app.ops import access
from app.ops.schemas import (
    ShiftCancel,
    ShiftConflictCheck,
    ShiftCreate,
    ShiftUpdate,
    TaskCreate,
    TaskUpdate,
    VisitCreate,
    VisitUpdate,
)
from app.records.pagination import offset_limit
from app.tenancy.context import OrganisationContext

VISIT_TRANSITIONS: dict[str, frozenset[str]] = {
    # Allow scheduled → completed for short visits that skip explicit start.
    "scheduled": frozenset({"confirmed", "in_progress", "completed", "cancelled", "missed"}),
    "confirmed": frozenset({"in_progress", "cancelled", "missed", "completed"}),
    "in_progress": frozenset({"completed", "cancelled", "missed"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
    "missed": frozenset(),
}

TASK_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"in_progress", "blocked", "cancelled", "completed"}),
    "in_progress": frozenset({"blocked", "completed", "cancelled", "open"}),
    "blocked": frozenset({"in_progress", "cancelled", "open"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


def _find_shift_overlap(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    staff_user_id: uuid.UUID,
    starts_at: datetime,
    ends_at: datetime,
    exclude_id: uuid.UUID | None = None,
) -> StaffShift | None:
    stmt = select(StaffShift).where(
        StaffShift.organisation_id == organisation_id,
        StaffShift.staff_user_id == staff_user_id,
        StaffShift.status == "scheduled",
        StaffShift.starts_at < ends_at,
        StaffShift.ends_at > starts_at,
    )
    if exclude_id is not None:
        stmt = stmt.where(StaffShift.id != exclude_id)
    return session.scalar(stmt.limit(1))


def check_shift_conflicts(
    session: Session,
    ctx: OrganisationContext,
    data: ShiftConflictCheck,
) -> dict:
    access.require_rota_read(ctx)
    access.assert_active_org_member(
        session, organisation_id=ctx.organisation_id, user_id=data.staff_user_id
    )
    if ctx.role == HMoreRole.SUPPORT_WORKER and data.staff_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    overlap = _find_shift_overlap(
        session,
        organisation_id=ctx.organisation_id,
        staff_user_id=data.staff_user_id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        exclude_id=data.exclude_shift_id,
    )
    return {
        "has_conflict": overlap is not None,
        "conflicting_shift_id": overlap.id if overlap is not None else None,
    }


def create_shift(session: Session, ctx: OrganisationContext, data: ShiftCreate) -> StaffShift:
    access.require_rota_manage(ctx)
    access.assert_active_org_member(
        session, organisation_id=ctx.organisation_id, user_id=data.staff_user_id
    )
    overlap = _find_shift_overlap(
        session,
        organisation_id=ctx.organisation_id,
        staff_user_id=data.staff_user_id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
    )
    if overlap is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Overlapping scheduled shift exists for this staff member",
        )
    row = StaffShift(
        organisation_id=ctx.organisation_id,
        staff_user_id=data.staff_user_id,
        created_by_user_id=ctx.user_id,
        shift_date=data.shift_date,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        timezone=data.timezone,
        shift_type=data.shift_type,
        location=data.location,
        notes=data.notes,
        status="scheduled",
    )
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.SHIFT_CREATE,
        resource_type="staff_shift",
        resource_id=row.id,
        summary="Staff shift created",
        metadata={"staff_user_id": str(data.staff_user_id)},
    )
    _schedule_shift_reminder(session, ctx, row)
    session.flush()
    session.refresh(row)
    return row


def list_shifts(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    staff_user_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[StaffShift], int]:
    access.require_rota_read(ctx)
    offset, limit = offset_limit(page, page_size)
    stmt = select(StaffShift).where(StaffShift.organisation_id == ctx.organisation_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(StaffShift.staff_user_id == ctx.user_id)
    if staff_user_id is not None:
        if ctx.role == HMoreRole.SUPPORT_WORKER and staff_user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        stmt = stmt.where(StaffShift.staff_user_id == staff_user_id)
    if date_from is not None:
        stmt = stmt.where(StaffShift.shift_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(StaffShift.shift_date <= date_to)
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        session.scalars(stmt.order_by(StaffShift.starts_at.asc()).offset(offset).limit(limit)).all()
    )
    return rows, total


def get_shift(session: Session, ctx: OrganisationContext, shift_id: uuid.UUID) -> StaffShift:
    access.require_rota_read(ctx)
    row = session.get(StaffShift, shift_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    if ctx.role == HMoreRole.SUPPORT_WORKER and row.staff_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return row


def update_shift(
    session: Session, ctx: OrganisationContext, shift_id: uuid.UUID, data: ShiftUpdate
) -> StaffShift:
    access.require_rota_manage(ctx)
    row = get_shift(session, ctx, shift_id)
    if row.status != "scheduled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only scheduled shifts can be updated")
    payload = data.model_dump(exclude_unset=True)
    starts = payload.get("starts_at", row.starts_at)
    ends = payload.get("ends_at", row.ends_at)
    if ends <= starts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ends_at must be later than starts_at")
    overlap = _find_shift_overlap(
        session,
        organisation_id=ctx.organisation_id,
        staff_user_id=row.staff_user_id,
        starts_at=starts,
        ends_at=ends,
        exclude_id=row.id,
    )
    if overlap is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Overlapping shift exists")
    for key, value in payload.items():
        setattr(row, key, value)
    if "starts_at" in payload:
        row.shift_date = starts.date()
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.SHIFT_UPDATE,
        resource_type="staff_shift",
        resource_id=row.id,
        summary="Staff shift updated",
    )
    session.refresh(row)
    return row


def cancel_shift(
    session: Session, ctx: OrganisationContext, shift_id: uuid.UUID, data: ShiftCancel
) -> StaffShift:
    access.require_rota_manage(ctx)
    row = get_shift(session, ctx, shift_id)
    if row.status != "scheduled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shift is not cancellable")
    row.status = "cancelled"
    row.cancel_reason = data.cancel_reason.strip()
    session.flush()
    _cancel_pending_reminders(session, ctx.organisation_id, "staff_shift", row.id)
    _audit(
        session,
        ctx,
        action=audit_events.SHIFT_CANCEL,
        resource_type="staff_shift",
        resource_id=row.id,
        summary="Staff shift cancelled",
    )
    session.refresh(row)
    return row


def create_visit(session: Session, ctx: OrganisationContext, data: VisitCreate) -> TenantVisit:
    access.assert_visit_assignee_scope(
        session,
        ctx,
        tenant_id=data.tenant_id,
        assignee_user_id=data.assigned_staff_user_id,
    )
    row = TenantVisit(
        organisation_id=ctx.organisation_id,
        tenant_id=data.tenant_id,
        assigned_staff_user_id=data.assigned_staff_user_id,
        created_by_user_id=ctx.user_id,
        scheduled_at=data.scheduled_at,
        expected_duration_minutes=data.expected_duration_minutes,
        timezone=data.timezone,
        visit_type=data.visit_type,
        purpose=data.purpose.strip(),
        location=data.location,
        notes=data.notes,
        status="scheduled",
    )
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.VISIT_SCHEDULE,
        resource_type="tenant_visit",
        resource_id=row.id,
        summary="Tenant visit scheduled",
        metadata={"tenant_id": str(data.tenant_id)},
    )
    _schedule_visit_reminder(session, ctx, row)
    session.flush()
    session.refresh(row)
    return row


def list_visits(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    tenant_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    upcoming_only: bool = False,
) -> tuple[list[TenantVisit], int]:
    access.require_visits_manage(ctx)
    offset, limit = offset_limit(page, page_size)
    stmt = select(TenantVisit).where(TenantVisit.organisation_id == ctx.organisation_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(TenantVisit.assigned_staff_user_id == ctx.user_id)
    if tenant_id is not None:
        if ctx.role == HMoreRole.SUPPORT_WORKER:
            access.assert_tenant_support_access(session, ctx, tenant_id)
        stmt = stmt.where(TenantVisit.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(TenantVisit.status == status_filter)
    if upcoming_only:
        stmt = stmt.where(
            TenantVisit.scheduled_at >= _now(),
            TenantVisit.status.in_(("scheduled", "confirmed")),
        )
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(TenantVisit.scheduled_at.asc()).offset(offset).limit(limit)
        ).all()
    )
    return rows, total


def get_visit(session: Session, ctx: OrganisationContext, visit_id: uuid.UUID) -> TenantVisit:
    access.require_visits_manage(ctx)
    row = session.get(TenantVisit, visit_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if ctx.role == HMoreRole.SUPPORT_WORKER and row.assigned_staff_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return row


def update_visit(
    session: Session, ctx: OrganisationContext, visit_id: uuid.UUID, data: VisitUpdate
) -> TenantVisit:
    row = get_visit(session, ctx, visit_id)
    payload = data.model_dump(exclude_unset=True)
    if "status" in payload:
        target = payload["status"]
        allowed = VISIT_TRANSITIONS.get(row.status, frozenset())
        if target != row.status and target not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition visit from {row.status} to {target}",
            )
        if target == "completed":
            row.completed_at = _now()
            if payload.get("linked_daily_log_id"):
                log = session.get(DailyLog, payload["linked_daily_log_id"])
                if (
                    log is None
                    or log.organisation_id != ctx.organisation_id
                    or log.tenant_id != row.tenant_id
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="linked_daily_log_id must belong to the same tenant/organisation",
                    )
        if target == "cancelled" and not (payload.get("cancel_reason") or row.cancel_reason):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cancel_reason is required when cancelling",
            )
    for key, value in payload.items():
        setattr(row, key, value)
    session.flush()
    action = audit_events.VISIT_UPDATE
    if row.status == "completed":
        action = audit_events.VISIT_COMPLETE
    elif row.status == "cancelled":
        action = audit_events.VISIT_CANCEL
        _cancel_pending_reminders(session, ctx.organisation_id, "tenant_visit", row.id)
    elif "scheduled_at" in payload:
        action = audit_events.VISIT_RESCHEDULE
        _schedule_visit_reminder(session, ctx, row)
    _audit(
        session,
        ctx,
        action=action,
        resource_type="tenant_visit",
        resource_id=row.id,
        summary=f"Visit {row.status}",
        metadata={"tenant_id": str(row.tenant_id)},
    )
    session.refresh(row)
    return row


def create_task(session: Session, ctx: OrganisationContext, data: TaskCreate) -> OperationalTask:
    access.assert_task_assignee_scope(
        session,
        ctx,
        assignee_user_id=data.assigned_user_id,
        tenant_id=data.tenant_id,
    )
    if data.visit_id is not None:
        visit = session.get(TenantVisit, data.visit_id)
        if visit is None or visit.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid visit_id")
    row = OperationalTask(
        organisation_id=ctx.organisation_id,
        title=data.title.strip(),
        description=data.description,
        assigned_user_id=data.assigned_user_id,
        created_by_user_id=ctx.user_id,
        tenant_id=data.tenant_id,
        visit_id=data.visit_id,
        priority=data.priority,
        due_at=data.due_at,
        status="open",
    )
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.TASK_CREATE,
        resource_type="operational_task",
        resource_id=row.id,
        summary="Task created",
        metadata={"assigned_user_id": str(data.assigned_user_id), "priority": data.priority},
    )
    if data.due_at is not None:
        _schedule_task_reminders(session, ctx, row)
    session.flush()
    session.refresh(row)
    return row


def list_tasks(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    assigned_user_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    priority: str | None = None,
    overdue_only: bool = False,
) -> tuple[list[OperationalTask], int]:
    access.require_tasks_manage(ctx)
    offset, limit = offset_limit(page, page_size)
    stmt = select(OperationalTask).where(OperationalTask.organisation_id == ctx.organisation_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(OperationalTask.assigned_user_id == ctx.user_id)
    if assigned_user_id is not None:
        if ctx.role == HMoreRole.SUPPORT_WORKER and assigned_user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        stmt = stmt.where(OperationalTask.assigned_user_id == assigned_user_id)
    if status_filter:
        stmt = stmt.where(OperationalTask.status == status_filter)
    if priority:
        stmt = stmt.where(OperationalTask.priority == priority)
    if overdue_only:
        stmt = stmt.where(
            OperationalTask.due_at.is_not(None),
            OperationalTask.due_at < _now(),
            OperationalTask.status.in_(("open", "in_progress", "blocked")),
        )
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(OperationalTask.due_at.asc().nullslast(), OperationalTask.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return rows, total


def get_task(session: Session, ctx: OrganisationContext, task_id: uuid.UUID) -> OperationalTask:
    access.require_tasks_manage(ctx)
    row = session.get(OperationalTask, task_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if ctx.role == HMoreRole.SUPPORT_WORKER and row.assigned_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return row


def update_task(
    session: Session, ctx: OrganisationContext, task_id: uuid.UUID, data: TaskUpdate
) -> OperationalTask:
    row = get_task(session, ctx, task_id)
    payload = data.model_dump(exclude_unset=True)
    if "assigned_user_id" in payload and payload["assigned_user_id"] is not None:
        access.assert_task_assignee_scope(
            session,
            ctx,
            assignee_user_id=payload["assigned_user_id"],
            tenant_id=row.tenant_id,
        )
    if "status" in payload:
        target = payload["status"]
        allowed = TASK_TRANSITIONS.get(row.status, frozenset())
        if target != row.status and target not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition task from {row.status} to {target}",
            )
        if target == "completed":
            row.completed_at = _now()
            _cancel_pending_reminders(session, ctx.organisation_id, "operational_task", row.id)
        if target == "cancelled":
            _cancel_pending_reminders(session, ctx.organisation_id, "operational_task", row.id)
    for key, value in payload.items():
        setattr(row, key, value)
    session.flush()
    action = audit_events.TASK_UPDATE
    if row.status == "completed":
        action = audit_events.TASK_COMPLETE
    elif "assigned_user_id" in payload:
        action = audit_events.TASK_ASSIGN
    _audit(
        session,
        ctx,
        action=action,
        resource_type="operational_task",
        resource_id=row.id,
        summary=f"Task {row.status}",
        metadata={"status": row.status, "priority": row.priority},
    )
    if "due_at" in payload and row.due_at is not None and row.status not in {"completed", "cancelled"}:
        _schedule_task_reminders(session, ctx, row)
    session.refresh(row)
    return row


def task_out_dict(row: OperationalTask) -> dict[str, Any]:
    overdue = bool(
        row.due_at
        and row.due_at < _now()
        and row.status in {"open", "in_progress", "blocked"}
    )
    return {
        "id": row.id,
        "organisation_id": row.organisation_id,
        "title": row.title,
        "description": row.description,
        "assigned_user_id": row.assigned_user_id,
        "created_by_user_id": row.created_by_user_id,
        "tenant_id": row.tenant_id,
        "visit_id": row.visit_id,
        "priority": row.priority,
        "due_at": row.due_at,
        "status": row.status,
        "completed_at": row.completed_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "overdue": overdue,
    }


def list_reminders(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    status_filter: str | None = None,
) -> tuple[list[ReminderRecord], int]:
    access.require_rota_read(ctx)
    offset, limit = offset_limit(page, page_size)
    stmt = select(ReminderRecord).where(ReminderRecord.organisation_id == ctx.organisation_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(ReminderRecord.recipient_user_id == ctx.user_id)
    if status_filter:
        stmt = stmt.where(ReminderRecord.status == status_filter)
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(ReminderRecord.scheduled_for.desc()).offset(offset).limit(limit)
        ).all()
    )
    return rows, total


def _upsert_reminder(
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
    if scheduled_for <= _now():
        return None
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
        channel="log",
        payload_summary=summary[:255],
    )
    session.add(row)
    session.flush()
    return row


def _cancel_pending_reminders(
    session: Session,
    organisation_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
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


def _schedule_shift_reminder(
    session: Session, ctx: OrganisationContext, shift: StaffShift
) -> None:
    settings = get_settings()
    lead = timedelta(minutes=settings.reminder_shift_lead_minutes)
    _upsert_reminder(
        session,
        organisation_id=ctx.organisation_id,
        resource_type="staff_shift",
        resource_id=shift.id,
        reminder_kind="shift_upcoming",
        recipient_user_id=shift.staff_user_id,
        scheduled_for=shift.starts_at - lead,
        summary=f"Upcoming shift {shift.shift_type}",
    )


def _schedule_visit_reminder(
    session: Session, ctx: OrganisationContext, visit: TenantVisit
) -> None:
    settings = get_settings()
    lead = timedelta(minutes=settings.reminder_visit_lead_minutes)
    _upsert_reminder(
        session,
        organisation_id=ctx.organisation_id,
        resource_type="tenant_visit",
        resource_id=visit.id,
        reminder_kind="visit_upcoming",
        recipient_user_id=visit.assigned_staff_user_id,
        scheduled_for=visit.scheduled_at - lead,
        summary=f"Upcoming visit: {visit.purpose}",
    )


def _schedule_task_reminders(
    session: Session, ctx: OrganisationContext, task: OperationalTask
) -> None:
    if task.due_at is None:
        return
    settings = get_settings()
    lead = timedelta(minutes=settings.reminder_task_due_lead_minutes)
    _upsert_reminder(
        session,
        organisation_id=ctx.organisation_id,
        resource_type="operational_task",
        resource_id=task.id,
        reminder_kind="task_due_soon",
        recipient_user_id=task.assigned_user_id,
        scheduled_for=task.due_at - lead,
        summary=f"Task due soon: {task.title}",
    )
    _upsert_reminder(
        session,
        organisation_id=ctx.organisation_id,
        resource_type="operational_task",
        resource_id=task.id,
        reminder_kind="task_overdue",
        recipient_user_id=task.assigned_user_id,
        scheduled_for=task.due_at + timedelta(minutes=1),
        summary=f"Task overdue: {task.title}",
    )

