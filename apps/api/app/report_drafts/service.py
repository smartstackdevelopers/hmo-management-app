"""F3.13 report draft service. Numbers from F2.14; AI narrative is draft-only."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event, record_event_independent
from app.core.config import Settings, get_settings
from app.db.models.report_drafts import OperationalReportDraft
from app.report_drafts import access as draft_access
from app.report_drafts.ai_client import generate_narrative
from app.report_drafts.metrics import collect_metrics
from app.report_drafts.periods import resolve_period
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation

NOTICE = "AI-GENERATED DRAFT — REQUIRES HUMAN REVIEW"


def _denied(ctx: OrganisationContext) -> None:
    record_event_independent(
        action=audit_events.REPORT_DRAFT_DENIED,
        resource_type="operational_report_draft",
        resource_id="",
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.DENIED,
        summary="Report draft access denied",
        metadata={},
    )


def _public(row: OperationalReportDraft) -> dict[str, Any]:
    body = row.edited_body if row.edited_body is not None else row.narrative_text
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "period_type": row.period_type,
        "period_start": row.period_start.isoformat(),
        "period_end": row.period_end.isoformat(),
        "timezone_name": row.timezone_name,
        "status": row.status,
        "version": row.version,
        "metrics": row.metrics_json or {},
        "narrative_text": row.narrative_text,
        "edited_body": row.edited_body,
        "display_body": body,
        "ai_status": row.ai_status,
        "ai_notice": NOTICE,
        "distributed": False,
        "auto_approved": False,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        "reviewed_by_user_id": str(row.reviewed_by_user_id) if row.reviewed_by_user_id else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "review_comment": row.review_comment,
    }


def generate_draft(
    session: Session,
    ctx: OrganisationContext,
    *,
    period_type: str,
    regenerate: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    try:
        draft_access.require_generate(ctx)
    except HTTPException:
        _denied(ctx)
        raise
    if period_type not in {"weekly", "monthly"}:
        raise HTTPException(status_code=422, detail="period_type must be weekly or monthly")
    period_start, period_end, tz_name = resolve_period(period_type)
    record_event(
        session,
        action=audit_events.REPORT_DRAFT_REQUESTED,
        resource_type="operational_report_draft",
        resource_id="",
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Report draft generation requested",
        metadata={"period_type": period_type, "period_start": period_start.isoformat()},
        raise_on_error=False,
    )
    latest = session.scalar(
        select(OperationalReportDraft)
        .where(
            OperationalReportDraft.organisation_id == ctx.organisation_id,
            OperationalReportDraft.period_type == period_type,
            OperationalReportDraft.period_start == period_start,
            OperationalReportDraft.period_end == period_end,
        )
        .order_by(OperationalReportDraft.version.desc())
        .limit(1)
    )
    if latest is not None and not regenerate:
        return _public(latest)
    version = 1 if latest is None else latest.version + 1
    metrics = collect_metrics(session, ctx, period_start=period_start, period_end=period_end)
    narrative = None
    ai_status = "skipped"
    if (settings.ai_service_base_url or "").strip() and (settings.ai_service_token or "").strip():
        try:
            ai = generate_narrative(
                settings,
                organisation_id=ctx.organisation_id,
                user_id=ctx.user_id,
                role=ctx.role.value,
                period_type=period_type,
                metrics=metrics,
            )
            narrative = str(ai.get("narrative") or "")[:8000] or None
            ai_status = "generated"
        except HTTPException as exc:
            if exc.status_code == 402:
                ai_status = "cap_reached"
                record_event(
                    session,
                    action=audit_events.REPORT_DRAFT_AI_FAILED,
                    resource_type="operational_report_draft",
                    resource_id="",
                    organisation_id=ctx.organisation_id,
                    actor_user_id=ctx.user_id,
                    actor_role=ctx.role.value,
                    outcome=AuditOutcome.DENIED,
                    summary="Report draft AI usage cap reached",
                    metadata={},
                    raise_on_error=False,
                )
            elif exc.status_code == 503:
                ai_status = "unavailable"
            else:
                ai_status = "failed"
                record_event(
                    session,
                    action=audit_events.REPORT_DRAFT_AI_FAILED,
                    resource_type="operational_report_draft",
                    resource_id="",
                    organisation_id=ctx.organisation_id,
                    actor_user_id=ctx.user_id,
                    actor_role=ctx.role.value,
                    outcome=AuditOutcome.FAILURE,
                    summary="Report draft AI narrative failed",
                    metadata={"status": exc.status_code},
                    raise_on_error=False,
                )
    row = OperationalReportDraft(
        organisation_id=ctx.organisation_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        timezone_name=tz_name,
        status="draft",
        version=version,
        metrics_json=metrics,
        narrative_text=narrative,
        edited_body=None,
        ai_status=ai_status,
        ai_notice=NOTICE,
        distributed=False,
        requested_by_user_id=ctx.user_id,
        generated_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.REPORT_DRAFT_GENERATED,
        resource_type="operational_report_draft",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Report draft generated",
        metadata={"ai_status": ai_status, "version": version, "period_type": period_type},
        raise_on_error=False,
    )
    return _public(row)


def list_drafts(session: Session, ctx: OrganisationContext, *, limit: int = 20) -> dict[str, Any]:
    try:
        draft_access.require_read(ctx)
    except HTTPException:
        _denied(ctx)
        raise
    rows = list(
        session.scalars(
            select(OperationalReportDraft)
            .where(OperationalReportDraft.organisation_id == ctx.organisation_id)
            .order_by(OperationalReportDraft.generated_at.desc())
            .limit(min(max(limit, 1), 100))
        )
    )
    return {"items": [_public(row) for row in rows], "ai_notice": NOTICE}


def get_draft(session: Session, ctx: OrganisationContext, draft_id: uuid.UUID) -> dict[str, Any]:
    try:
        draft_access.require_read(ctx)
    except HTTPException:
        _denied(ctx)
        raise
    row = session.get(OperationalReportDraft, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Report draft not found")
    assert_same_organisation(ctx, row.organisation_id)
    return _public(row)


def edit_draft(
    session: Session,
    ctx: OrganisationContext,
    draft_id: uuid.UUID,
    *,
    edited_body: str,
) -> dict[str, Any]:
    try:
        draft_access.require_review(ctx)
    except HTTPException:
        _denied(ctx)
        raise
    row = session.get(OperationalReportDraft, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Report draft not found")
    assert_same_organisation(ctx, row.organisation_id)
    if row.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft reports can be edited")
    row.edited_body = edited_body[:20000]
    session.flush()
    record_event(
        session,
        action=audit_events.REPORT_DRAFT_EDITED,
        resource_type="operational_report_draft",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Report draft edited",
        metadata={},
        raise_on_error=False,
    )
    return _public(row)


def review_draft(
    session: Session,
    ctx: OrganisationContext,
    draft_id: uuid.UUID,
    *,
    decision: str,
    review_comment: str | None,
) -> dict[str, Any]:
    try:
        draft_access.require_review(ctx)
    except HTTPException:
        _denied(ctx)
        raise
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail="decision must be approve or reject")
    row = session.get(OperationalReportDraft, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Report draft not found")
    assert_same_organisation(ctx, row.organisation_id)
    if row.status != "draft":
        raise HTTPException(status_code=409, detail="Report already reviewed")
    row.status = "approved" if decision == "approve" else "rejected"
    row.reviewed_by_user_id = ctx.user_id
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_comment = review_comment
    row.distributed = False
    session.flush()
    action = audit_events.REPORT_DRAFT_APPROVED if decision == "approve" else audit_events.REPORT_DRAFT_REJECTED
    record_event(
        session,
        action=action,
        resource_type="operational_report_draft",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Report draft reviewed",
        metadata={"decision": decision, "distributed": False},
        raise_on_error=False,
    )
    return _public(row)


def next_version_count(session: Session, organisation_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(OperationalReportDraft).where(
                OperationalReportDraft.organisation_id == organisation_id
            )
        )
        or 0
    )
