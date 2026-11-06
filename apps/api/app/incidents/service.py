"""F2.4 incident reports, follow-ups, reminders, and workload aggregation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import get_settings
from app.db.models.enums import HMoreRole
from app.db.models.incidents import Incident, IncidentFollowUp, IncidentStatusHistory
from app.db.models.scheduling import OperationalTask, ReminderRecord, TenantVisit
from app.db.models.support_ops import CaseAssignment, Handover
from app.incidents import access
from app.incidents.schemas import (
    FollowUpCreate,
    FollowUpUpdate,
    IncidentCreate,
    IncidentUpdate,
    WorkloadResponse,
    WorkloadStaffSummary,
)
from app.records.pagination import offset_limit
from app.tenancy.context import OrganisationContext

INCIDENT_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"submitted"}),
    "submitted": frozenset({"under_review", "action_required", "closed"}),
    "under_review": frozenset({"action_required", "resolved", "closed"}),
    "action_required": frozenset({"under_review", "resolved", "closed"}),
    "resolved": frozenset({"closed", "reopened"}),
    "closed": frozenset({"reopened"}),
    "reopened": frozenset({"under_review", "action_required", "resolved", "closed"}),
}

FOLLOW_UP_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"in_progress", "blocked", "completed", "cancelled"}),
    "in_progress": frozenset({"blocked", "completed", "cancelled", "open"}),
    "blocked": frozenset({"in_progress", "cancelled", "open"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}

OPEN_FOLLOW_UP = ("open", "in_progress", "blocked")


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


def _next_reference(session: Session, organisation_id: uuid.UUID) -> str:
    year = _now().year
    prefix = f"INC-{year}-"
    count = (
        session.scalar(
            select(func.count())
            .select_from(Incident)
            .where(
                Incident.organisation_id == organisation_id,
                Incident.reference_number.like(f"{prefix}%"),
            )
        )
        or 0
    )
    return f"{prefix}{count + 1:05d}"


def _record_status_change(
    session: Session,
    ctx: OrganisationContext,
    incident: Incident,
    *,
    from_status: str | None,
    to_status: str,
    note: str | None = None,
) -> None:
    session.add(
        IncidentStatusHistory(
            organisation_id=ctx.organisation_id,
            incident_id=incident.id,
            from_status=from_status,
            to_status=to_status,
            changed_by_user_id=ctx.user_id,
            note=note,
        )
    )


def _open_follow_up_count(session: Session, incident_id: uuid.UUID) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(IncidentFollowUp)
            .where(
                IncidentFollowUp.incident_id == incident_id,
                IncidentFollowUp.status.in_(OPEN_FOLLOW_UP),
            )
        )
        or 0
    )


def incident_out_dict(session: Session, row: Incident) -> dict[str, Any]:
    return {
        "id": row.id,
        "organisation_id": row.organisation_id,
        "reference_number": row.reference_number,
        "title": row.title,
        "category": row.category,
        "description": row.description,
        "occurred_at": row.occurred_at,
        "reported_by_user_id": row.reported_by_user_id,
        "reviewer_user_id": row.reviewer_user_id,
        "tenant_id": row.tenant_id,
        "property_id": row.property_id,
        "room_id": row.room_id,
        "location": row.location,
        "severity": row.severity,
        "immediate_actions": row.immediate_actions,
        "people_involved": row.people_involved,
        "witnesses": row.witnesses,
        "status": row.status,
        "resolution_notes": row.resolution_notes,
        "submitted_at": row.submitted_at,
        "closed_at": row.closed_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "open_follow_up_count": _open_follow_up_count(session, row.id),
    }


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
) -> None:
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
        return
    session.add(
        ReminderRecord(
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
    )


def _cancel_pending(
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


def schedule_follow_up_reminders(
    session: Session, ctx: OrganisationContext, action: IncidentFollowUp
) -> None:
    settings = get_settings()
    _cancel_pending(session, ctx.organisation_id, "incident_follow_up", action.id)
    if action.status in {"completed", "cancelled"} or action.due_at is None:
        return
    lead = timedelta(minutes=settings.reminder_incident_follow_up_lead_minutes)
    _upsert_reminder(
        session,
        organisation_id=ctx.organisation_id,
        resource_type="incident_follow_up",
        resource_id=action.id,
        reminder_kind="incident_follow_up_due_soon",
        recipient_user_id=action.assigned_user_id,
        scheduled_for=action.due_at - lead,
        summary=f"Incident follow-up due soon ({action.incident_id})",
    )
    _upsert_reminder(
        session,
        organisation_id=ctx.organisation_id,
        resource_type="incident_follow_up",
        resource_id=action.id,
        reminder_kind="incident_follow_up_overdue",
        recipient_user_id=action.assigned_user_id,
        scheduled_for=action.due_at + timedelta(minutes=1),
        summary=f"Incident follow-up overdue ({action.incident_id})",
    )


def create_incident(
    session: Session, ctx: OrganisationContext, data: IncidentCreate
) -> Incident:
    access.require_incident_create(ctx)
    access.assert_incident_links(
        session,
        ctx,
        tenant_id=data.tenant_id,
        property_id=data.property_id,
        room_id=data.room_id,
    )
    occurred = data.occurred_at if data.occurred_at.tzinfo else data.occurred_at.replace(
        tzinfo=timezone.utc
    )
    row = Incident(
        organisation_id=ctx.organisation_id,
        reference_number=_next_reference(session, ctx.organisation_id),
        title=data.title,
        category=data.category,
        description=data.description,
        occurred_at=occurred,
        reported_by_user_id=ctx.user_id,
        tenant_id=data.tenant_id,
        property_id=data.property_id,
        room_id=data.room_id,
        location=data.location,
        severity=data.severity,
        immediate_actions=data.immediate_actions,
        people_involved=data.people_involved,
        witnesses=data.witnesses,
        status="draft",
    )
    session.add(row)
    session.flush()
    _record_status_change(session, ctx, row, from_status=None, to_status="draft", note="Created")
    _audit(
        session,
        ctx,
        action=audit_events.INCIDENT_CREATE,
        resource_type="incident",
        resource_id=row.id,
        summary="Incident created",
        metadata={"category": row.category, "severity": row.severity, "ref": row.reference_number},
    )
    if data.submit:
        return transition_incident(session, ctx, row.id, "submitted")
    return row


def get_incident(session: Session, ctx: OrganisationContext, incident_id: uuid.UUID) -> Incident:
    access.require_incident_read(ctx)
    row = session.get(Incident, incident_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    access.assert_can_view_incident(ctx, row)
    return row


def list_incidents(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    status_filter: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    q: str | None = None,
) -> tuple[list[Incident], int]:
    access.require_incident_read(ctx)
    stmt = select(Incident).where(Incident.organisation_id == ctx.organisation_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(
            or_(
                Incident.reported_by_user_id == ctx.user_id,
                Incident.reviewer_user_id == ctx.user_id,
            )
        )
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)
    if category:
        stmt = stmt.where(Incident.category == category)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Incident.title.ilike(like), Incident.reference_number.ilike(like))
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(stmt.order_by(Incident.occurred_at.desc()).offset(offset).limit(limit)).all()
    )
    return rows, total


def update_incident(
    session: Session, ctx: OrganisationContext, incident_id: uuid.UUID, data: IncidentUpdate
) -> Incident:
    row = get_incident(session, ctx, incident_id)
    payload = data.model_dump(exclude_unset=True)
    status_note = payload.pop("status_note", None)
    target_status = payload.pop("status", None)
    reviewer = payload.pop("reviewer_user_id", None) if "reviewer_user_id" in payload else None

    # Draft edits by reporter or OA; submitted content changes require manage.
    if row.status != "draft" and ctx.role == HMoreRole.SUPPORT_WORKER:
        if target_status is None and payload:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Support workers cannot amend submitted incidents",
            )

    if any(k in payload for k in ("tenant_id", "property_id", "room_id")):
        access.assert_incident_links(
            session,
            ctx,
            tenant_id=payload.get("tenant_id", row.tenant_id),
            property_id=payload.get("property_id", row.property_id),
            room_id=payload.get("room_id", row.room_id),
        )

    if reviewer is not None:
        if ctx.role not in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        access.assert_active_org_member(
            session, organisation_id=ctx.organisation_id, user_id=reviewer
        )
        row.reviewer_user_id = reviewer
        _audit(
            session,
            ctx,
            action=audit_events.INCIDENT_ASSIGN,
            resource_type="incident",
            resource_id=row.id,
            summary="Incident reviewer assigned",
        )
        _upsert_reminder(
            session,
            organisation_id=ctx.organisation_id,
            resource_type="incident",
            resource_id=row.id,
            reminder_kind="incident_assigned",
            recipient_user_id=reviewer,
            scheduled_for=_now() + timedelta(minutes=1),
            summary=f"Incident assigned: {row.reference_number}",
        )

    for key, value in payload.items():
        setattr(row, key, value)
    if "occurred_at" in payload and row.occurred_at.tzinfo is None:
        row.occurred_at = row.occurred_at.replace(tzinfo=timezone.utc)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.INCIDENT_UPDATE,
        resource_type="incident",
        resource_id=row.id,
        summary="Incident updated",
        metadata={"status": row.status},
    )
    if target_status is not None:
        return transition_incident(session, ctx, row.id, target_status, note=status_note)
    return row


def transition_incident(
    session: Session,
    ctx: OrganisationContext,
    incident_id: uuid.UUID,
    target: str,
    *,
    note: str | None = None,
) -> Incident:
    row = get_incident(session, ctx, incident_id)
    allowed = INCIDENT_TRANSITIONS.get(row.status, frozenset())
    if target != row.status and target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition incident from {row.status} to {target}",
        )
    if target == "submitted" and ctx.role == HMoreRole.SUPPORT_WORKER:
        if row.reported_by_user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if target in {"closed", "resolved", "reopened", "under_review", "action_required"}:
        if ctx.role not in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}:
            # Reviewer may move under_review / action_required / resolved
            if not (
                row.reviewer_user_id == ctx.user_id
                and target in {"under_review", "action_required", "resolved"}
            ):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if target == "closed":
        if not row.resolution_notes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="resolution_notes required before closing",
            )
        outstanding = _open_follow_up_count(session, row.id)
        if outstanding > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot close incident while follow-up actions remain open",
            )
        row.closed_at = _now()
    if target == "submitted" and row.submitted_at is None:
        row.submitted_at = _now()
    if target == "reopened":
        row.closed_at = None

    prev = row.status
    row.status = target
    session.flush()
    _record_status_change(session, ctx, row, from_status=prev, to_status=target, note=note)
    action = audit_events.INCIDENT_STATUS_CHANGE
    if target == "submitted":
        action = audit_events.INCIDENT_SUBMIT
    elif target == "closed":
        action = audit_events.INCIDENT_CLOSE
    elif target == "reopened":
        action = audit_events.INCIDENT_REOPEN
    _audit(
        session,
        ctx,
        action=action,
        resource_type="incident",
        resource_id=row.id,
        summary=f"Incident status {prev} → {target}",
        metadata={"from": prev, "to": target},
    )
    return row


def list_incident_history(
    session: Session, ctx: OrganisationContext, incident_id: uuid.UUID
) -> list[IncidentStatusHistory]:
    get_incident(session, ctx, incident_id)
    return list(
        session.scalars(
            select(IncidentStatusHistory)
            .where(
                IncidentStatusHistory.organisation_id == ctx.organisation_id,
                IncidentStatusHistory.incident_id == incident_id,
            )
            .order_by(IncidentStatusHistory.created_at.asc())
        ).all()
    )


def create_follow_up(
    session: Session, ctx: OrganisationContext, incident_id: uuid.UUID, data: FollowUpCreate
) -> IncidentFollowUp:
    incident = get_incident(session, ctx, incident_id)
    if incident.status in {"closed", "draft"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Follow-ups require a submitted incident that is not closed",
        )
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        access.require_incident_create(ctx)
    else:
        access.require_incident_manage(ctx)
    access.assert_active_org_member(
        session, organisation_id=ctx.organisation_id, user_id=data.assigned_user_id
    )
    due = data.due_at
    if due is not None and due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    row = IncidentFollowUp(
        organisation_id=ctx.organisation_id,
        incident_id=incident.id,
        description=data.description,
        assigned_user_id=data.assigned_user_id,
        created_by_user_id=ctx.user_id,
        priority=data.priority,
        due_at=due,
        status="open",
    )
    session.add(row)
    session.flush()
    schedule_follow_up_reminders(session, ctx, row)
    _audit(
        session,
        ctx,
        action=audit_events.INCIDENT_FOLLOW_UP_CREATE,
        resource_type="incident_follow_up",
        resource_id=row.id,
        summary="Incident follow-up created",
        metadata={"incident_id": str(incident.id), "priority": row.priority},
    )
    return row


def get_follow_up(
    session: Session, ctx: OrganisationContext, follow_up_id: uuid.UUID
) -> IncidentFollowUp:
    access.require_incident_read(ctx)
    row = session.get(IncidentFollowUp, follow_up_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    get_incident(session, ctx, row.incident_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER and row.assigned_user_id != ctx.user_id:
        # Still allow if they can view the parent incident
        incident = session.get(Incident, row.incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        access.assert_can_view_incident(ctx, incident)
    return row


def list_follow_ups(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    incident_id: uuid.UUID | None = None,
    overdue_only: bool = False,
    assigned_user_id: uuid.UUID | None = None,
) -> tuple[list[IncidentFollowUp], int]:
    access.require_incident_read(ctx)
    stmt = select(IncidentFollowUp).where(
        IncidentFollowUp.organisation_id == ctx.organisation_id
    )
    if incident_id is not None:
        get_incident(session, ctx, incident_id)
        stmt = stmt.where(IncidentFollowUp.incident_id == incident_id)
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(IncidentFollowUp.assigned_user_id == ctx.user_id)
    if assigned_user_id is not None and ctx.role != HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(IncidentFollowUp.assigned_user_id == assigned_user_id)
    if overdue_only:
        stmt = stmt.where(
            IncidentFollowUp.due_at.is_not(None),
            IncidentFollowUp.due_at < _now(),
            IncidentFollowUp.status.in_(OPEN_FOLLOW_UP),
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(
            stmt.order_by(IncidentFollowUp.due_at.asc().nulls_last()).offset(offset).limit(limit)
        ).all()
    )
    return rows, total


def update_follow_up(
    session: Session,
    ctx: OrganisationContext,
    follow_up_id: uuid.UUID,
    data: FollowUpUpdate,
) -> IncidentFollowUp:
    row = get_follow_up(session, ctx, follow_up_id)
    payload = data.model_dump(exclude_unset=True)
    if "assigned_user_id" in payload:
        if ctx.role not in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        access.assert_active_org_member(
            session, organisation_id=ctx.organisation_id, user_id=payload["assigned_user_id"]
        )
        _audit(
            session,
            ctx,
            action=audit_events.INCIDENT_FOLLOW_UP_ASSIGN,
            resource_type="incident_follow_up",
            resource_id=row.id,
            summary="Follow-up reassigned",
        )
    if "status" in payload:
        target = payload["status"]
        allowed = FOLLOW_UP_TRANSITIONS.get(row.status, frozenset())
        if target != row.status and target not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition follow-up from {row.status} to {target}",
            )
        if target == "completed":
            row.completed_at = _now()
            row.completed_by_user_id = ctx.user_id
            _audit(
                session,
                ctx,
                action=audit_events.INCIDENT_FOLLOW_UP_COMPLETE,
                resource_type="incident_follow_up",
                resource_id=row.id,
                summary="Follow-up completed",
            )
    for key, value in payload.items():
        setattr(row, key, value)
    if "due_at" in payload and row.due_at is not None and row.due_at.tzinfo is None:
        row.due_at = row.due_at.replace(tzinfo=timezone.utc)
    session.flush()
    schedule_follow_up_reminders(session, ctx, row)
    return row


def _staff_ids_for_workload(
    session: Session, ctx: OrganisationContext, staff_user_id: uuid.UUID | None
) -> list[uuid.UUID]:
    access.require_workload_read(ctx)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        return [ctx.user_id]
    if staff_user_id is not None:
        access.assert_active_org_member(
            session, organisation_id=ctx.organisation_id, user_id=staff_user_id
        )
        return [staff_user_id]
    # Org-level: staff with active case assignments or open tasks/follow-ups
    ids = set(
        session.scalars(
            select(CaseAssignment.support_worker_user_id).where(
                CaseAssignment.organisation_id == ctx.organisation_id,
                CaseAssignment.status == "active",
            )
        ).all()
    )
    ids.update(
        session.scalars(
            select(OperationalTask.assigned_user_id).where(
                OperationalTask.organisation_id == ctx.organisation_id,
                OperationalTask.status.in_(("open", "in_progress", "blocked")),
            )
        ).all()
    )
    ids.update(
        session.scalars(
            select(IncidentFollowUp.assigned_user_id).where(
                IncidentFollowUp.organisation_id == ctx.organisation_id,
                IncidentFollowUp.status.in_(OPEN_FOLLOW_UP),
            )
        ).all()
    )
    return sorted(ids, key=str)


def get_workload(
    session: Session,
    ctx: OrganisationContext,
    *,
    staff_user_id: uuid.UUID | None = None,
) -> WorkloadResponse:
    staff_ids = _staff_ids_for_workload(session, ctx, staff_user_id)
    now = _now()
    soon = now + timedelta(days=7)
    summaries: list[WorkloadStaffSummary] = []
    for uid in staff_ids:
        assigned_tenants = (
            session.scalar(
                select(func.count())
                .select_from(CaseAssignment)
                .where(
                    CaseAssignment.organisation_id == ctx.organisation_id,
                    CaseAssignment.support_worker_user_id == uid,
                    CaseAssignment.status == "active",
                )
            )
            or 0
        )
        open_tasks = (
            session.scalar(
                select(func.count())
                .select_from(OperationalTask)
                .where(
                    OperationalTask.organisation_id == ctx.organisation_id,
                    OperationalTask.assigned_user_id == uid,
                    OperationalTask.status.in_(("open", "in_progress", "blocked")),
                )
            )
            or 0
        )
        overdue_tasks = (
            session.scalar(
                select(func.count())
                .select_from(OperationalTask)
                .where(
                    OperationalTask.organisation_id == ctx.organisation_id,
                    OperationalTask.assigned_user_id == uid,
                    OperationalTask.status.in_(("open", "in_progress", "blocked")),
                    OperationalTask.due_at.is_not(None),
                    OperationalTask.due_at < now,
                )
            )
            or 0
        )
        upcoming_visits = (
            session.scalar(
                select(func.count())
                .select_from(TenantVisit)
                .where(
                    TenantVisit.organisation_id == ctx.organisation_id,
                    TenantVisit.assigned_staff_user_id == uid,
                    TenantVisit.status.in_(("scheduled", "confirmed")),
                    TenantVisit.scheduled_at >= now,
                    TenantVisit.scheduled_at <= soon,
                )
            )
            or 0
        )
        pending_handovers = (
            session.scalar(
                select(func.count())
                .select_from(Handover)
                .where(
                    Handover.organisation_id == ctx.organisation_id,
                    or_(
                        Handover.recipient_user_id == uid,
                        Handover.created_by_user_id == uid,
                    ),
                    Handover.status.in_(("draft", "submitted", "acknowledged")),
                )
            )
            or 0
        )
        open_fu = (
            session.scalar(
                select(func.count())
                .select_from(IncidentFollowUp)
                .where(
                    IncidentFollowUp.organisation_id == ctx.organisation_id,
                    IncidentFollowUp.assigned_user_id == uid,
                    IncidentFollowUp.status.in_(OPEN_FOLLOW_UP),
                )
            )
            or 0
        )
        overdue_fu = (
            session.scalar(
                select(func.count())
                .select_from(IncidentFollowUp)
                .where(
                    IncidentFollowUp.organisation_id == ctx.organisation_id,
                    IncidentFollowUp.assigned_user_id == uid,
                    IncidentFollowUp.status.in_(OPEN_FOLLOW_UP),
                    IncidentFollowUp.due_at.is_not(None),
                    IncidentFollowUp.due_at < now,
                )
            )
            or 0
        )
        summaries.append(
            WorkloadStaffSummary(
                staff_user_id=uid,
                assigned_tenants=assigned_tenants,
                open_tasks=open_tasks,
                overdue_tasks=overdue_tasks,
                upcoming_visits=upcoming_visits,
                pending_handovers=pending_handovers,
                open_incident_follow_ups=open_fu,
                overdue_incident_follow_ups=overdue_fu,
            )
        )
    scope = "own" if ctx.role == HMoreRole.SUPPORT_WORKER else "organisation"
    return WorkloadResponse(
        organisation_id=ctx.organisation_id,
        scope=scope,
        staff=summaries,
    )
