"""Housing application reporting (F2.5 data only)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.housing import HousingApplication
from app.reporting.access import require_housing_reports
from app.reporting.filters import HousingReportFilters
from app.records.pagination import offset_limit
from app.tenancy.context import OrganisationContext

HOUSING_STATUSES = (
    "draft",
    "submitted",
    "under_review",
    "information_required",
    "approved",
    "rejected",
    "withdrawn",
    "closed",
)


def _date_column(field: str):
    if field == "submitted_at":
        return HousingApplication.submitted_at
    if field == "updated_at":
        return HousingApplication.updated_at
    return HousingApplication.created_at


def _base_stmt(ctx: OrganisationContext, flt: HousingReportFilters):
    stmt = select(HousingApplication).where(HousingApplication.organisation_id == ctx.organisation_id)
    col = _date_column(flt.date_field)
    if flt.created_from:
        stmt = stmt.where(col >= flt.created_from)
    if flt.created_to:
        stmt = stmt.where(col <= flt.created_to)
    if flt.status:
        stmt = stmt.where(HousingApplication.status == flt.status)
    if flt.reviewer_user_id:
        stmt = stmt.where(HousingApplication.reviewer_user_id == flt.reviewer_user_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(HousingApplication.reviewer_user_id == ctx.user_id)
    return stmt


def housing_summary(session: Session, ctx: OrganisationContext, flt: HousingReportFilters) -> dict[str, Any]:
    require_housing_reports(ctx)
    flt.validate_window()
    counts: dict[str, int] = {s: 0 for s in HOUSING_STATUSES}
    stmt = (
        select(HousingApplication.status, func.count())
        .where(HousingApplication.organisation_id == ctx.organisation_id)
        .group_by(HousingApplication.status)
    )
    col = _date_column(flt.date_field)
    if flt.created_from:
        stmt = stmt.where(col >= flt.created_from)
    if flt.created_to:
        stmt = stmt.where(col <= flt.created_to)
    if flt.reviewer_user_id:
        stmt = stmt.where(HousingApplication.reviewer_user_id == flt.reviewer_user_id)
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        stmt = stmt.where(HousingApplication.reviewer_user_id == ctx.user_id)
    for status, cnt in session.execute(stmt).all():
        if status in counts:
            counts[status] = int(cnt)
    total = sum(counts.values())
    trends_stmt = (
        select(func.date_trunc("day", col), func.count())
        .where(HousingApplication.organisation_id == ctx.organisation_id)
        .group_by(func.date_trunc("day", col))
        .order_by(func.date_trunc("day", col))
    )
    if flt.created_from:
        trends_stmt = trends_stmt.where(col >= flt.created_from)
    if flt.created_to:
        trends_stmt = trends_stmt.where(col <= flt.created_to)
    trends = [
        {"date": (row[0].date().isoformat() if row[0] else None), "count": int(row[1])}
        for row in session.execute(trends_stmt).all()
        if row[0]
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date_field": flt.date_field,
        "total": total,
        "by_status": counts,
        "awaiting_information": counts.get("information_required", 0),
        "approved_count": counts.get("approved", 0),
        "rejected_count": counts.get("rejected", 0),
        "trends_daily": trends,
        "definitions": {
            "date_field": f"Counts filtered by {flt.date_field}",
            "trends": "Daily submission/creation counts in range",
        },
    }


def housing_rows(session: Session, ctx: OrganisationContext, flt: HousingReportFilters) -> tuple[list[dict[str, Any]], int]:
    require_housing_reports(ctx)
    flt.validate_window()
    base = _base_stmt(ctx, flt)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    offset, limit = offset_limit(flt.page, flt.page_size)
    rows = session.scalars(base.order_by(HousingApplication.created_at.desc()).offset(offset).limit(limit)).all()
    items = [
        {
            "id": str(r.id),
            "reference_number": r.reference_number,
            "status": r.status,
            "priority": r.priority,
            "reviewer_user_id": str(r.reviewer_user_id) if r.reviewer_user_id else None,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return items, int(total)
