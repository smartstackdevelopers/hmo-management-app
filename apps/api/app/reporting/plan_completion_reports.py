"""Support plan completion analytics (F6.2 / F2.10 data)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.support_plans import SupportPlanGoal, TenantSupportPlan
from app.reporting.access import require_plans_reports
from app.reporting.filters import PlanReportFilters
from app.records.pagination import offset_limit
from app.tenancy.context import OrganisationContext

PLAN_STATUSES = ("draft", "active", "under_review", "on_hold", "completed", "closed")
GOAL_ACHIEVED = "achieved"


def _base(ctx: OrganisationContext, flt: PlanReportFilters):
    stmt = select(TenantSupportPlan).where(TenantSupportPlan.organisation_id == ctx.organisation_id)
    if flt.created_from:
        stmt = stmt.where(TenantSupportPlan.created_at >= flt.created_from)
    if flt.created_to:
        stmt = stmt.where(TenantSupportPlan.created_at <= flt.created_to)
    if flt.status:
        stmt = stmt.where(TenantSupportPlan.status == flt.status)
    worker = flt.support_worker_user_id
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        worker = ctx.user_id
    if worker:
        stmt = stmt.where(TenantSupportPlan.responsible_worker_user_id == worker)
    return stmt


def plan_completion_summary(
    session: Session, ctx: OrganisationContext, flt: PlanReportFilters
) -> dict[str, Any]:
    require_plans_reports(ctx)
    flt.validate_window()
    today = date.today()
    counts: dict[str, int] = {s: 0 for s in PLAN_STATUSES}
    stmt = (
        select(TenantSupportPlan.status, func.count())
        .where(TenantSupportPlan.organisation_id == ctx.organisation_id)
        .group_by(TenantSupportPlan.status)
    )
    if flt.created_from:
        stmt = stmt.where(TenantSupportPlan.created_at >= flt.created_from)
    if flt.created_to:
        stmt = stmt.where(TenantSupportPlan.created_at <= flt.created_to)
    worker = flt.support_worker_user_id
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        worker = ctx.user_id
    if worker:
        stmt = stmt.where(TenantSupportPlan.responsible_worker_user_id == worker)
    for status, cnt in session.execute(stmt).all():
        if status in counts:
            counts[status] = int(cnt)
    total = sum(counts.values())
    pending_reviews = int(
        session.scalar(
            select(func.count())
            .select_from(TenantSupportPlan)
            .where(
                TenantSupportPlan.organisation_id == ctx.organisation_id,
                TenantSupportPlan.status.in_(("active", "under_review")),
                TenantSupportPlan.planned_review_date.is_not(None),
                TenantSupportPlan.planned_review_date >= today,
            )
        )
        or 0
    )
    overdue_reviews_q = select(func.count()).select_from(TenantSupportPlan).where(
        TenantSupportPlan.organisation_id == ctx.organisation_id,
        TenantSupportPlan.status.in_(("active", "under_review")),
        TenantSupportPlan.planned_review_date.is_not(None),
        TenantSupportPlan.planned_review_date < today,
    )
    if worker:
        overdue_reviews_q = overdue_reviews_q.where(TenantSupportPlan.responsible_worker_user_id == worker)
    overdue_reviews = int(session.scalar(overdue_reviews_q) or 0)

    goals_total = int(
        session.scalar(
            select(func.count()).select_from(SupportPlanGoal).where(
                SupportPlanGoal.organisation_id == ctx.organisation_id
            )
        )
        or 0
    )
    goals_achieved = int(
        session.scalar(
            select(func.count()).select_from(SupportPlanGoal).where(
                SupportPlanGoal.organisation_id == ctx.organisation_id,
                SupportPlanGoal.status == GOAL_ACHIEVED,
            )
        )
        or 0
    )
    goal_rate = round((goals_achieved / goals_total) * 100, 1) if goals_total else 0.0

    day_bucket = func.date_trunc("day", TenantSupportPlan.created_at).label("day_bucket")
    trends_stmt = (
        select(day_bucket, func.count())
        .where(TenantSupportPlan.organisation_id == ctx.organisation_id)
        .group_by(day_bucket)
        .order_by(day_bucket)
    )
    if flt.created_from:
        trends_stmt = trends_stmt.where(TenantSupportPlan.created_at >= flt.created_from)
    if flt.created_to:
        trends_stmt = trends_stmt.where(TenantSupportPlan.created_at <= flt.created_to)
    if worker:
        trends_stmt = trends_stmt.where(TenantSupportPlan.responsible_worker_user_id == worker)
    trends = [
        {"date": (row[0].date().isoformat() if row[0] else None), "count": int(row[1])}
        for row in session.execute(trends_stmt).all()
        if row[0]
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "by_status": counts,
        "active_plans": counts.get("active", 0) + counts.get("under_review", 0),
        "completed_plans": counts.get("completed", 0),
        "pending_reviews": pending_reviews,
        "overdue_reviews": overdue_reviews,
        "goals_total": goals_total,
        "goals_achieved": goals_achieved,
        "goal_completion_rate": goal_rate,
        "trends_daily": trends,
        "definitions": {
            "overdue_reviews": "Active/under_review plans with planned_review_date before today",
            "goal_completion_rate": "Achieved goals / all goals in organisation scope",
        },
    }


def plan_completion_rows(
    session: Session, ctx: OrganisationContext, flt: PlanReportFilters
) -> tuple[list[dict[str, Any]], int]:
    require_plans_reports(ctx)
    flt.validate_window()
    base = _base(ctx, flt)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    offset, limit = offset_limit(flt.page, flt.page_size)
    rows = session.scalars(
        base.order_by(TenantSupportPlan.created_at.desc()).offset(offset).limit(limit)
    ).all()
    today = date.today()
    items = []
    for r in rows:
        overdue = (
            r.status in ("active", "under_review")
            and r.planned_review_date is not None
            and r.planned_review_date < today
        )
        items.append(
            {
                "id": str(r.id),
                "reference_number": r.reference_number,
                "title": r.title,
                "status": r.status,
                "tenant_id": str(r.tenant_id),
                "responsible_worker_user_id": str(r.responsible_worker_user_id),
                "planned_review_date": r.planned_review_date.isoformat() if r.planned_review_date else None,
                "review_overdue": overdue,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return items, int(total)
