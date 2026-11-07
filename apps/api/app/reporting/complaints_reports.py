"""Complaints reporting (F2.7 operational deadlines — not statutory)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.complaints import Complaint
from app.reporting.access import require_complaints_reports
from app.reporting.filters import ComplaintsReportFilters
from app.records.pagination import offset_limit
from app.tenancy.context import OrganisationContext

OPEN_STATUSES = frozenset(
    {"submitted", "acknowledged", "under_review", "investigation", "awaiting_information", "escalated", "reopened"}
)


def _date_column(field: str):
    if field == "updated_at":
        return Complaint.updated_at
    return Complaint.created_at


def _apply_filters(stmt, ctx: OrganisationContext, flt: ComplaintsReportFilters):
    stmt = stmt.where(Complaint.organisation_id == ctx.organisation_id)
    col = _date_column(flt.date_field)
    if flt.created_from:
        stmt = stmt.where(col >= flt.created_from)
    if flt.created_to:
        stmt = stmt.where(col <= flt.created_to)
    if flt.status:
        stmt = stmt.where(Complaint.status == flt.status)
    if flt.priority:
        stmt = stmt.where(Complaint.priority == flt.priority)
    if flt.escalated_only:
        stmt = stmt.where(Complaint.status == "escalated")
    if flt.overdue_only:
        now = datetime.now(timezone.utc)
        stmt = stmt.where(
            Complaint.response_due_at.is_not(None),
            Complaint.response_due_at < now,
            Complaint.status.in_(tuple(OPEN_STATUSES)),
        )
    return stmt


def complaints_summary(session: Session, ctx: OrganisationContext, flt: ComplaintsReportFilters) -> dict[str, Any]:
    require_complaints_reports(ctx)
    flt.validate_window()
    now = datetime.now(timezone.utc)
    by_status: dict[str, int] = {}
    stmt = select(Complaint.status, func.count()).select_from(Complaint)
    stmt = _apply_filters(stmt, ctx, flt).group_by(Complaint.status)
    for status, cnt in session.execute(stmt).all():
        by_status[str(status)] = int(cnt)
    total = sum(by_status.values())
    by_priority_stmt = select(Complaint.priority, func.count()).select_from(Complaint)
    by_priority_stmt = _apply_filters(by_priority_stmt, ctx, flt).group_by(Complaint.priority)
    by_priority = {str(p): int(c) for p, c in session.execute(by_priority_stmt).all()}
    overdue_stmt = select(func.count()).select_from(Complaint)
    overdue_stmt = _apply_filters(overdue_stmt, ctx, flt).where(
        Complaint.response_due_at.is_not(None),
        Complaint.response_due_at < now,
        Complaint.status.in_(tuple(OPEN_STATUSES)),
    )
    overdue = int(session.scalar(overdue_stmt) or 0)
    open_count = sum(by_status.get(s, 0) for s in OPEN_STATUSES)
    col = _date_column(flt.date_field)
    day_bucket = func.date_trunc("day", col).label("day_bucket")
    trends_stmt = (
        select(day_bucket, func.count())
        .where(Complaint.organisation_id == ctx.organisation_id)
        .group_by(day_bucket)
        .order_by(day_bucket)
    )
    if flt.created_from:
        trends_stmt = trends_stmt.where(col >= flt.created_from)
    if flt.created_to:
        trends_stmt = trends_stmt.where(col <= flt.created_to)
    trends = [
        {"date": row[0].date().isoformat(), "count": int(row[1])}
        for row in session.execute(trends_stmt).all()
        if row[0]
    ]
    return {
        "generated_at": now.isoformat(),
        "total": total,
        "open_complaints": open_count,
        "under_investigation": by_status.get("investigation", 0),
        "awaiting_information": by_status.get("awaiting_information", 0),
        "escalated": by_status.get("escalated", 0),
        "overdue_operational": overdue,
        "resolved": by_status.get("resolved", 0),
        "closed": by_status.get("closed", 0),
        "by_status": by_status,
        "by_priority": by_priority,
        "trends_daily": trends,
        "definitions": {
            "overdue_operational": "response_due_at passed while complaint still open (org-configured deadline, not statutory)",
        },
    }


def complaints_rows(
    session: Session, ctx: OrganisationContext, flt: ComplaintsReportFilters
) -> tuple[list[dict[str, Any]], int]:
    require_complaints_reports(ctx)
    flt.validate_window()
    stmt = select(Complaint)
    stmt = _apply_filters(stmt, ctx, flt)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(flt.page, flt.page_size)
    rows = session.scalars(stmt.order_by(Complaint.created_at.desc()).offset(offset).limit(limit)).all()
    items = [
        {
            "reference_number": r.reference_number,
            "title": r.title,
            "status": r.status,
            "priority": r.priority,
            "response_due_at": r.response_due_at.isoformat() if r.response_due_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return items, int(total)
