"""F2.1 caseload, daily log, and handover services."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.enums import HMoreRole
from app.db.models.support_ops import CaseAssignment, DailyLog, Handover
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.records.pagination import offset_limit
from app.support import access
from app.support.schemas import (
    CaseAssignmentCreate,
    DailyLogCreate,
    DailyLogUpdate,
    HandoverCreate,
    HandoverUpdate,
)
from app.tenancy.context import OrganisationContext

HANDOVER_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"submitted", "cancelled"}),
    "submitted": frozenset({"acknowledged", "cancelled"}),
    "acknowledged": frozenset({"completed", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assignment_out(row: CaseAssignment, *, extras: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "id": row.id,
        "organisation_id": row.organisation_id,
        "tenant_id": row.tenant_id,
        "support_worker_user_id": row.support_worker_user_id,
        "assigned_by_user_id": row.assigned_by_user_id,
        "status": row.status,
        "assigned_at": row.assigned_at,
        "ended_at": row.ended_at,
        "assignment_notes": row.assignment_notes,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "tenant_preferred_name": None,
        "tenant_full_name": None,
        "support_worker_display_name": None,
        "recent_log_count": None,
        "pending_handover_count": None,
    }
    if extras:
        payload.update(extras)
    return payload


def create_assignment(
    session: Session, ctx: OrganisationContext, data: CaseAssignmentCreate
) -> dict[str, Any]:
    access.require_caseload_assign(ctx)
    tenant = access.get_tenant_or_404(session, ctx, data.tenant_id)
    access.assert_worker_is_support_member(
        session,
        organisation_id=ctx.organisation_id,
        worker_user_id=data.support_worker_user_id,
    )
    existing = access.active_assignment_for_worker(
        session,
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        worker_user_id=data.support_worker_user_id,
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active assignment already exists for this worker and tenant",
        )

    row = CaseAssignment(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        support_worker_user_id=data.support_worker_user_id,
        assigned_by_user_id=ctx.user_id,
        status="active",
        assigned_at=_now(),
        assignment_notes=data.assignment_notes,
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.CASELOAD_ASSIGN,
        resource_type="case_assignment",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Case assignment created",
        metadata={
            "tenant_id": str(tenant.id),
            "support_worker_user_id": str(data.support_worker_user_id),
        },
    )
    session.flush()
    session.refresh(row)
    return _assignment_out(row)


def end_assignment(
    session: Session, ctx: OrganisationContext, assignment_id: uuid.UUID
) -> dict[str, Any]:
    access.require_caseload_assign(ctx)
    row = session.get(CaseAssignment, assignment_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if row.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment is not active")
    row.status = "ended"
    row.ended_at = _now()
    session.flush()
    record_event(
        session,
        action=audit_events.CASELOAD_ASSIGN_END,
        resource_type="case_assignment",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Case assignment ended",
        metadata={"tenant_id": str(row.tenant_id)},
    )
    session.flush()
    session.refresh(row)
    return _assignment_out(row)


def list_caseload(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    status_filter: str = "active",
) -> tuple[list[dict[str, Any]], int]:
    access.require_caseload_read(ctx)
    offset, limit = offset_limit(page, page_size)

    stmt = (
        select(CaseAssignment, Tenant, User)
        .join(Tenant, Tenant.id == CaseAssignment.tenant_id)
        .join(User, User.id == CaseAssignment.support_worker_user_id)
        .where(CaseAssignment.organisation_id == ctx.organisation_id)
    )
    if status_filter:
        stmt = stmt.where(CaseAssignment.status == status_filter)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(CaseAssignment.support_worker_user_id == ctx.user_id)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Tenant.preferred_name.ilike(pattern),
                Tenant.full_name.ilike(pattern),
                Tenant.tenancy_reference.ilike(pattern),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(session.scalar(count_stmt) or 0)
    rows = session.execute(
        stmt.order_by(CaseAssignment.assigned_at.desc()).offset(offset).limit(limit)
    ).all()

    items: list[dict[str, Any]] = []
    for assignment, tenant, worker in rows:
        log_count = session.scalar(
            select(func.count())
            .select_from(DailyLog)
            .where(
                DailyLog.organisation_id == ctx.organisation_id,
                DailyLog.tenant_id == tenant.id,
                DailyLog.status != "voided",
            )
        )
        pending = session.scalar(
            select(func.count())
            .select_from(Handover)
            .where(
                Handover.organisation_id == ctx.organisation_id,
                Handover.tenant_id == tenant.id,
                Handover.status.in_(("submitted", "acknowledged")),
            )
        )
        items.append(
            _assignment_out(
                assignment,
                extras={
                    "tenant_preferred_name": tenant.preferred_name,
                    "tenant_full_name": tenant.full_name,
                    "support_worker_display_name": worker.display_name,
                    "recent_log_count": int(log_count or 0),
                    "pending_handover_count": int(pending or 0),
                },
            )
        )
    return items, total


def get_case_detail(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID
) -> dict[str, Any]:
    tenant = access.assert_tenant_support_access(session, ctx, tenant_id)
    assignments = session.scalars(
        select(CaseAssignment)
        .where(
            CaseAssignment.organisation_id == ctx.organisation_id,
            CaseAssignment.tenant_id == tenant.id,
        )
        .order_by(CaseAssignment.assigned_at.desc())
    ).all()
    logs, log_total = list_daily_logs(
        session, ctx, tenant_id=tenant.id, page=1, page_size=10
    )
    handovers, handover_total = list_handovers(
        session, ctx, tenant_id=tenant.id, page=1, page_size=10
    )
    return {
        "tenant": {
            "id": tenant.id,
            "organisation_id": tenant.organisation_id,
            "preferred_name": tenant.preferred_name,
            "full_name": tenant.full_name,
            "email": tenant.email,
            "phone": tenant.phone,
            "tenancy_reference": tenant.tenancy_reference,
            "status": tenant.status.value if hasattr(tenant.status, "value") else tenant.status,
        },
        "assignments": [_assignment_out(a) for a in assignments],
        "recent_logs": logs,
        "recent_logs_total": log_total,
        "recent_handovers": handovers,
        "recent_handovers_total": handover_total,
    }


def create_daily_log(
    session: Session, ctx: OrganisationContext, data: DailyLogCreate
) -> DailyLog:
    access.require_daily_log_write(ctx)
    tenant = access.assert_tenant_support_access(session, ctx, data.tenant_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        # Already gated by assignment in assert_tenant_support_access
        pass
    row = DailyLog(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        author_user_id=ctx.user_id,
        log_date=data.log_date or date.today(),
        logged_at=_now(),
        activity_category=data.activity_category,
        summary=data.summary,
        notes=data.notes,
        interaction_type=data.interaction_type,
        follow_up_required=data.follow_up_required,
        next_action=data.next_action,
        status="active",
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.DAILY_LOG_CREATE,
        resource_type="daily_log",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Daily log created",
        metadata={
            "tenant_id": str(tenant.id),
            "activity_category": row.activity_category,
            "follow_up_required": row.follow_up_required,
            # Do not store note body in audit metadata.
        },
    )
    session.flush()
    session.refresh(row)
    return row


def list_daily_logs(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[DailyLog], int]:
    access.require_caseload_read(ctx)
    offset, limit = offset_limit(page, page_size)
    stmt = select(DailyLog).where(DailyLog.organisation_id == ctx.organisation_id)
    if tenant_id is not None:
        access.assert_tenant_support_access(session, ctx, tenant_id)
        stmt = stmt.where(DailyLog.tenant_id == tenant_id)
    elif ctx.role == HMoreRole.SUPPORT_WORKER:
        assigned_tenant_ids = select(CaseAssignment.tenant_id).where(
            CaseAssignment.organisation_id == ctx.organisation_id,
            CaseAssignment.support_worker_user_id == ctx.user_id,
            CaseAssignment.status == "active",
        )
        stmt = stmt.where(DailyLog.tenant_id.in_(assigned_tenant_ids))

    count = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        session.scalars(stmt.order_by(DailyLog.log_date.desc(), DailyLog.logged_at.desc())
        .offset(offset)
        .limit(limit)).all()
    )
    return rows, count


def get_daily_log(
    session: Session, ctx: OrganisationContext, log_id: uuid.UUID
) -> DailyLog:
    row = session.get(DailyLog, log_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily log not found")
    access.assert_tenant_support_access(session, ctx, row.tenant_id)
    return row


def update_daily_log(
    session: Session,
    ctx: OrganisationContext,
    log_id: uuid.UUID,
    data: DailyLogUpdate,
) -> DailyLog:
    access.require_daily_log_oversight_edit(ctx)
    row = get_daily_log(session, ctx, log_id)
    if row.status == "voided":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Log is voided")

    if ctx.role == HMoreRole.SUPPORT_WORKER and row.author_user_id != ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Support Workers may only amend their own logs",
        )

    payload = data.model_dump(exclude_unset=True)
    if "status" in payload:
        new_status = payload["status"]
        if new_status == "voided":
            if ctx.role not in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Organisation Admin may void daily logs",
                )
        elif new_status == "amended":
            pass
        elif new_status != row.status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported status transition to {new_status}",
            )

    for key, value in payload.items():
        setattr(row, key, value)
    if payload and "status" not in payload and row.status == "active":
        row.status = "amended"

    session.flush()
    record_event(
        session,
        action=audit_events.DAILY_LOG_UPDATE,
        resource_type="daily_log",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Daily log updated",
        metadata={"tenant_id": str(row.tenant_id), "status": row.status},
    )
    session.flush()
    session.refresh(row)
    return row


def create_handover(
    session: Session, ctx: OrganisationContext, data: HandoverCreate
) -> Handover:
    access.require_daily_log_write(ctx)  # same create permission gate for SW
    if ctx.role not in {HMoreRole.SUPPORT_WORKER, HMoreRole.SUPER_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Support Workers may create handovers",
        )
    tenant = access.assert_tenant_support_access(session, ctx, data.tenant_id)
    access.assert_worker_is_support_member(
        session,
        organisation_id=ctx.organisation_id,
        worker_user_id=data.recipient_user_id,
    )
    if data.recipient_user_id == ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipient must be a different support worker",
        )

    row = Handover(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        created_by_user_id=ctx.user_id,
        recipient_user_id=data.recipient_user_id,
        handover_at=data.handover_at or _now(),
        summary=data.summary,
        case_updates=data.case_updates,
        outstanding_tasks=data.outstanding_tasks,
        follow_up_actions=data.follow_up_actions,
        priority=data.priority,
        status="submitted" if data.submit else "draft",
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=(
            audit_events.HANDOVER_SUBMIT if data.submit else audit_events.HANDOVER_CREATE
        ),
        resource_type="handover",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary="Handover submitted" if data.submit else "Handover draft created",
        metadata={
            "tenant_id": str(tenant.id),
            "recipient_user_id": str(data.recipient_user_id),
            "priority": row.priority,
            "status": row.status,
        },
    )
    session.flush()
    session.refresh(row)
    return row


def list_handovers(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    pending_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Handover], int]:
    access.require_caseload_read(ctx)
    offset, limit = offset_limit(page, page_size)
    stmt = select(Handover).where(Handover.organisation_id == ctx.organisation_id)
    if tenant_id is not None:
        access.assert_tenant_support_access(session, ctx, tenant_id)
        stmt = stmt.where(Handover.tenant_id == tenant_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(
            or_(
                Handover.created_by_user_id == ctx.user_id,
                Handover.recipient_user_id == ctx.user_id,
                Handover.tenant_id.in_(
                    select(CaseAssignment.tenant_id).where(
                        CaseAssignment.organisation_id == ctx.organisation_id,
                        CaseAssignment.support_worker_user_id == ctx.user_id,
                        CaseAssignment.status == "active",
                    )
                ),
            )
        )
    if status_filter:
        stmt = stmt.where(Handover.status == status_filter)
    if pending_only:
        stmt = stmt.where(Handover.status.in_(("submitted", "acknowledged")))

    count = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(Handover.handover_at.desc()).offset(offset).limit(limit)
        ).all()
    )
    return rows, count


def get_handover(
    session: Session, ctx: OrganisationContext, handover_id: uuid.UUID
) -> Handover:
    row = session.get(Handover, handover_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handover not found")
    access.assert_tenant_support_access(session, ctx, row.tenant_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        allowed = {
            row.created_by_user_id,
            row.recipient_user_id,
        }
        assignment = access.active_assignment_for_worker(
            session,
            organisation_id=ctx.organisation_id,
            tenant_id=row.tenant_id,
            worker_user_id=ctx.user_id,
        )
        if ctx.user_id not in allowed and assignment is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return row


def update_handover_draft(
    session: Session,
    ctx: OrganisationContext,
    handover_id: uuid.UUID,
    data: HandoverUpdate,
) -> Handover:
    row = get_handover(session, ctx, handover_id)
    if row.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft handovers can be edited",
        )
    if ctx.role == HMoreRole.SUPPORT_WORKER and row.created_by_user_id != ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator may edit this handover",
        )
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.flush()
    session.flush()
    session.refresh(row)
    return row


def transition_handover(
    session: Session,
    ctx: OrganisationContext,
    handover_id: uuid.UUID,
    *,
    target_status: str,
) -> Handover:
    row = get_handover(session, ctx, handover_id)
    allowed = HANDOVER_TRANSITIONS.get(row.status, frozenset())
    if target_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {row.status} to {target_status}",
        )

    is_admin = ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}

    if target_status == "submitted":
        if row.created_by_user_id != ctx.user_id and ctx.role != HMoreRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the creator may submit this handover",
            )
        action = audit_events.HANDOVER_SUBMIT
    elif target_status == "acknowledged":
        if row.recipient_user_id != ctx.user_id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the recipient may acknowledge this handover",
            )
        row.acknowledged_at = _now()
        row.acknowledged_by_user_id = ctx.user_id
        action = audit_events.HANDOVER_ACKNOWLEDGE
    elif target_status == "completed":
        if ctx.user_id not in {row.recipient_user_id, row.created_by_user_id} and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not permitted to complete this handover",
            )
        row.completed_at = _now()
        action = audit_events.HANDOVER_COMPLETE
    elif target_status == "cancelled":
        if ctx.user_id != row.created_by_user_id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not permitted to cancel this handover",
            )
        action = audit_events.HANDOVER_CANCEL
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown status")

    row.status = target_status
    session.flush()
    record_event(
        session,
        action=action,
        resource_type="handover",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary=f"Handover {target_status}",
        metadata={"tenant_id": str(row.tenant_id), "status": row.status},
    )
    session.flush()
    session.refresh(row)
    return row
