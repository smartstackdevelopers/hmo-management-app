"""Support worker caseload reporting (F2.1 / F2.2 / F2.9)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.scheduling import TenantVisit
from app.db.models.support_ops import CaseAssignment, Handover
from app.db.models.enums import RecordStatus
from app.db.models.tenant import Tenant
from app.db.models.tenant_timeline import TenantFollowUp
from app.reporting.access import require_caseload_reports
from app.reporting.filters import CaseloadReportFilters
from app.records.pagination import offset_limit
from app.tenancy.context import OrganisationContext

OPEN_FOLLOWUP = ("open", "in_progress", "awaiting_information")
PENDING_HANDOVER = ("submitted", "acknowledged")


def _worker_filter(ctx: OrganisationContext, worker_id: uuid.UUID | None) -> uuid.UUID | None:
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        return ctx.user_id
    return worker_id


def caseload_summary(session: Session, ctx: OrganisationContext, flt: CaseloadReportFilters) -> dict[str, Any]:
    require_caseload_reports(ctx)
    flt.validate_window()
    worker = _worker_filter(ctx, flt.support_worker_user_id)
    now = datetime.now(timezone.utc)
    assign_stmt = select(func.count()).select_from(CaseAssignment).where(
        CaseAssignment.organisation_id == ctx.organisation_id,
        CaseAssignment.status == "active",
    )
    if worker:
        assign_stmt = assign_stmt.where(CaseAssignment.support_worker_user_id == worker)
    active_assignments = int(session.scalar(assign_stmt) or 0)
    workers_stmt = select(func.count(func.distinct(CaseAssignment.support_worker_user_id))).where(
        CaseAssignment.organisation_id == ctx.organisation_id,
        CaseAssignment.status == "active",
    )
    support_workers = int(session.scalar(workers_stmt) or 0)
    assigned_tenants = int(
        session.scalar(
            select(func.count(func.distinct(CaseAssignment.tenant_id))).where(
                CaseAssignment.organisation_id == ctx.organisation_id,
                CaseAssignment.status == "active",
            )
        )
        or 0
    )
    total_tenants = int(
        session.scalar(
            select(func.count()).select_from(Tenant).where(
                Tenant.organisation_id == ctx.organisation_id,
                Tenant.status == RecordStatus.ACTIVE,
            )
        )
        or 0
    )
    unassigned = max(0, total_tenants - assigned_tenants)
    fu_stmt = select(func.count()).select_from(TenantFollowUp).where(
        TenantFollowUp.organisation_id == ctx.organisation_id,
        TenantFollowUp.status.in_(OPEN_FOLLOWUP),
    )
    if worker:
        fu_stmt = fu_stmt.where(TenantFollowUp.assigned_user_id == worker)
    open_followups = int(session.scalar(fu_stmt) or 0)
    overdue_fu_stmt = select(func.count()).select_from(TenantFollowUp).where(
        TenantFollowUp.organisation_id == ctx.organisation_id,
        TenantFollowUp.status.in_(OPEN_FOLLOWUP),
        TenantFollowUp.due_at.is_not(None),
        TenantFollowUp.due_at < now,
    )
    if worker:
        overdue_fu_stmt = overdue_fu_stmt.where(TenantFollowUp.assigned_user_id == worker)
    overdue_fu = int(session.scalar(overdue_fu_stmt) or 0)
    ho_stmt = select(func.count()).select_from(Handover).where(
        Handover.organisation_id == ctx.organisation_id,
        Handover.status.in_(PENDING_HANDOVER),
    )
    if worker:
        ho_stmt = ho_stmt.where(
            (Handover.recipient_user_id == worker) | (Handover.created_by_user_id == worker)
        )
    pending_handovers = int(session.scalar(ho_stmt) or 0)
    visit_stmt = select(func.count()).select_from(TenantVisit).where(
        TenantVisit.organisation_id == ctx.organisation_id,
        TenantVisit.scheduled_at >= now,
        TenantVisit.status.in_(("scheduled", "confirmed")),
    )
    if worker:
        visit_stmt = visit_stmt.where(TenantVisit.assigned_staff_user_id == worker)
    upcoming_visits = int(session.scalar(visit_stmt) or 0)
    dist_stmt = (
        select(CaseAssignment.support_worker_user_id, func.count())
        .where(
            CaseAssignment.organisation_id == ctx.organisation_id,
            CaseAssignment.status == "active",
        )
        .group_by(CaseAssignment.support_worker_user_id)
    )
    distribution = [
        {"support_worker_user_id": str(uid), "active_tenant_count": int(cnt)}
        for uid, cnt in session.execute(dist_stmt).all()
    ]
    return {
        "generated_at": now.isoformat(),
        "support_workers_with_caseload": support_workers,
        "active_assignments": active_assignments,
        "assigned_tenants": assigned_tenants,
        "unassigned_tenants": unassigned,
        "open_follow_ups": open_followups,
        "overdue_follow_ups": overdue_fu,
        "pending_handovers": pending_handovers,
        "upcoming_visits": upcoming_visits,
        "distribution_by_worker": distribution,
        "definitions": {
            "unassigned_tenants": "Tenants without an active case assignment (not a performance score)",
            "overdue_follow_ups": "Follow-ups with due_at in the past and status still open",
        },
    }


def caseload_rows(
    session: Session, ctx: OrganisationContext, flt: CaseloadReportFilters
) -> tuple[list[dict[str, Any]], int]:
    require_caseload_reports(ctx)
    flt.validate_window()
    worker = _worker_filter(ctx, flt.support_worker_user_id)
    stmt = select(CaseAssignment).where(
        CaseAssignment.organisation_id == ctx.organisation_id,
        CaseAssignment.status == "active",
    )
    if worker:
        stmt = stmt.where(CaseAssignment.support_worker_user_id == worker)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(flt.page, flt.page_size)
    rows = session.scalars(stmt.order_by(CaseAssignment.assigned_at.desc()).offset(offset).limit(limit)).all()
    items = [
        {
            "assignment_id": str(r.id),
            "tenant_id": str(r.tenant_id),
            "support_worker_user_id": str(r.support_worker_user_id),
            "assigned_at": r.assigned_at.isoformat() if r.assigned_at else None,
        }
        for r in rows
    ]
    return items, int(total)
