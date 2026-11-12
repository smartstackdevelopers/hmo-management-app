"""Scheduled report job management (F6.2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.membership import OrganisationMembership
from app.db.models.enums import MembershipStatus
from app.db.models.reporting_analytics import ScheduledReport, ScheduledReportRun
from app.db.models.user import User
from app.reporting.access import require_schedule_manage
from app.tenancy.context import OrganisationContext

VALID_CATEGORIES = frozenset({"occupancy", "housing", "complaints", "caseload", "plans", "dashboard"})
VALID_FREQ = frozenset({"daily", "weekly", "monthly"})
VALID_FORMATS = frozenset({"csv", "pdf", "xlsx"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def next_run_after(freq: str, from_dt: datetime | None = None) -> datetime:
    base = from_dt or _now()
    if freq == "daily":
        return base + timedelta(days=1)
    if freq == "weekly":
        return base + timedelta(days=7)
    return base + timedelta(days=30)


def _validate_recipients(session: Session, ctx: OrganisationContext, recipient_ids: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in recipient_ids:
        try:
            uid = uuid.UUID(str(raw))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid recipient id: {raw}") from exc
        membership = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == ctx.organisation_id,
                OrganisationMembership.user_id == uid,
                OrganisationMembership.status == MembershipStatus.ACTIVE,
            )
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipient {uid} is not an active member of this organisation",
            )
        user = session.get(User, uid)
        if user is None:
            raise HTTPException(status_code=400, detail=f"Recipient user not found: {uid}")
        cleaned.append(str(uid))
    if not cleaned:
        raise HTTPException(status_code=400, detail="At least one authorised recipient is required")
    return cleaned


def create_schedule(
    session: Session,
    ctx: OrganisationContext,
    *,
    name: str,
    report_category: str,
    frequency: str,
    export_format: str = "csv",
    period_days: int = 7,
    filters: dict[str, Any] | None = None,
    recipient_user_ids: list[str] | None = None,
    is_enabled: bool = True,
) -> dict[str, Any]:
    require_schedule_manage(ctx)
    if report_category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid report category")
    if frequency not in VALID_FREQ:
        raise HTTPException(status_code=400, detail="Invalid frequency")
    if export_format not in VALID_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid export format")
    if period_days < 1 or period_days > 366:
        raise HTTPException(status_code=400, detail="period_days must be 1–366")
    recipients = _validate_recipients(session, ctx, recipient_user_ids or [])
    row = ScheduledReport(
        organisation_id=ctx.organisation_id,
        name=name.strip()[:200],
        report_category=report_category,
        export_format=export_format,
        frequency=frequency,
        period_days=period_days,
        filters_json=filters or {},
        recipient_user_ids=recipients,
        is_enabled=is_enabled,
        next_run_at=_now() if is_enabled else None,
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.REPORTS_SCHEDULE_CREATE,
        resource_type="scheduled_report",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Created scheduled {report_category} report",
        raise_on_error=False,
    )
    return schedule_to_dict(row)


def update_schedule(
    session: Session,
    ctx: OrganisationContext,
    schedule_id: uuid.UUID,
    *,
    name: str | None = None,
    is_enabled: bool | None = None,
    recipient_user_ids: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    period_days: int | None = None,
) -> dict[str, Any]:
    require_schedule_manage(ctx)
    row = session.get(ScheduledReport, schedule_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if name is not None:
        row.name = name.strip()[:200]
    if filters is not None:
        row.filters_json = filters
    if period_days is not None:
        if period_days < 1 or period_days > 366:
            raise HTTPException(status_code=400, detail="period_days must be 1–366")
        row.period_days = period_days
    if recipient_user_ids is not None:
        row.recipient_user_ids = _validate_recipients(session, ctx, recipient_user_ids)
    if is_enabled is not None:
        row.is_enabled = is_enabled
        if is_enabled and row.next_run_at is None:
            row.next_run_at = _now()
        if not is_enabled:
            row.next_run_at = None
    row.updated_by_user_id = ctx.user_id
    session.flush()
    record_event(
        session,
        action=audit_events.REPORTS_SCHEDULE_UPDATE,
        resource_type="scheduled_report",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Updated scheduled report",
        raise_on_error=False,
    )
    return schedule_to_dict(row)


def list_schedules(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_schedule_manage(ctx)
    rows = session.scalars(
        select(ScheduledReport)
        .where(ScheduledReport.organisation_id == ctx.organisation_id)
        .order_by(ScheduledReport.created_at.desc())
    ).all()
    return [schedule_to_dict(r) for r in rows]


def list_runs(
    session: Session, ctx: OrganisationContext, schedule_id: uuid.UUID | None = None, *, limit: int = 50
) -> list[dict[str, Any]]:
    require_schedule_manage(ctx)
    stmt = select(ScheduledReportRun).where(ScheduledReportRun.organisation_id == ctx.organisation_id)
    if schedule_id:
        stmt = stmt.where(ScheduledReportRun.scheduled_report_id == schedule_id)
    rows = session.scalars(stmt.order_by(ScheduledReportRun.created_at.desc()).limit(limit)).all()
    return [run_to_dict(r) for r in rows]


def schedule_to_dict(row: ScheduledReport) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "report_category": row.report_category,
        "export_format": row.export_format,
        "frequency": row.frequency,
        "period_days": row.period_days,
        "filters": row.filters_json,
        "recipient_user_ids": row.recipient_user_ids,
        "is_enabled": row.is_enabled,
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def run_to_dict(row: ScheduledReportRun) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "scheduled_report_id": str(row.scheduled_report_id),
        "status": row.status,
        "attempt_count": row.attempt_count,
        "error_message": row.error_message,
        "report_export_id": str(row.report_export_id) if row.report_export_id else None,
        "period_from": row.period_from.isoformat() if row.period_from else None,
        "period_to": row.period_to.isoformat() if row.period_to else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
