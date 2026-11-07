"""F3.8 analysis pipeline: deterministic checklist first, AI for the gap narrative only."""

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
from app.db.models.housing import HousingApplication, WaitingListEntry
from app.db.models.housing_application_analysis import (
    HousingApplicationAnalysis,
    HousingApplicationAnalysisFinding,
)
from app.housing_application_analysis import access as analysis_access
from app.housing_application_analysis.ai_client import explain_gaps
from app.housing_application_analysis.checklist import (
    evaluate_application,
    heuristic_gap_narrative,
    validate_ai_narrative,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation


def _denied(ctx: OrganisationContext, *, application_id: uuid.UUID | None = None) -> None:
    record_event_independent(
        action=audit_events.AI_HOUSING_APPLICATION_DENIED,
        resource_type="housing_application",
        resource_id=str(application_id or ""),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.DENIED,
        summary="Housing application analysis access denied",
        metadata={"application_id": str(application_id) if application_id else None},
    )


def _guard(ctx: OrganisationContext, fn, *, application_id: uuid.UUID | None = None):
    try:
        return fn()
    except HTTPException as exc:
        if exc.status_code == 403:
            _denied(ctx, application_id=application_id)
        raise


def _public(
    row: HousingApplicationAnalysis,
    findings: list[HousingApplicationAnalysisFinding],
    *,
    current_fingerprint: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "application_id": str(row.application_id),
        "version_number": row.version_number,
        "status": row.status,
        "checklist_summary": row.checklist_summary_json or {},
        "gap_narrative": row.gap_narrative,
        "source_refs": row.source_refs_json or [],
        "ai_status": row.ai_status,
        "ai_error": row.ai_error,
        "generation_method": row.generation_method,
        "prompt_id": row.prompt_id,
        "prompt_version": row.prompt_version,
        "provider": row.provider,
        "model_id": row.model_id,
        "feature_id": row.feature_id,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        "requested_by_user_id": str(row.requested_by_user_id) if row.requested_by_user_id else None,
        "reviewed_by_user_id": str(row.reviewed_by_user_id) if row.reviewed_by_user_id else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "review_comment": row.review_comment,
        "stale": current_fingerprint is not None and current_fingerprint != row.source_fingerprint,
        "source_fingerprint": row.source_fingerprint,
        "legal_certification": False,
        "housing_decision": False,
        "notice": (
            "AI assistance only — this analysis does not determine housing eligibility, "
            "allocation, approval, or rejection. Final decisions remain with authorised human staff."
        ),
        "findings": [
            {
                "id": str(item.id),
                "code": item.code,
                "source": item.source,
                "outcome": item.outcome,
                "title": item.title,
                "detail": item.detail,
                "recommended_action": item.recommended_action,
                "related_checklist_item_id": str(item.related_checklist_item_id)
                if item.related_checklist_item_id
                else None,
                "related_file_id": str(item.related_file_id) if item.related_file_id else None,
                "needs_human_verification": item.needs_human_verification,
                "review_status": item.review_status,
            }
            for item in findings
        ],
    }


def _load_findings(session: Session, analysis_id: uuid.UUID) -> list[HousingApplicationAnalysisFinding]:
    return list(
        session.scalars(
            select(HousingApplicationAnalysisFinding).where(
                HousingApplicationAnalysisFinding.analysis_id == analysis_id
            )
        )
    )


def _next_version(session: Session, organisation_id: uuid.UUID, application_id: uuid.UUID) -> int:
    current = session.scalar(
        select(func.max(HousingApplicationAnalysis.version_number)).where(
            HousingApplicationAnalysis.organisation_id == organisation_id,
            HousingApplicationAnalysis.application_id == application_id,
        )
    )
    return int(current or 0) + 1


def _latest(session: Session, organisation_id: uuid.UUID, application_id: uuid.UUID) -> HousingApplicationAnalysis | None:
    return session.scalars(
        select(HousingApplicationAnalysis)
        .where(
            HousingApplicationAnalysis.organisation_id == organisation_id,
            HousingApplicationAnalysis.application_id == application_id,
        )
        .order_by(HousingApplicationAnalysis.version_number.desc())
        .limit(1)
    ).first()


def _snapshot_application(session: Session, application: HousingApplication) -> dict[str, Any]:
    waiting = session.scalar(
        select(WaitingListEntry).where(
            WaitingListEntry.organisation_id == application.organisation_id,
            WaitingListEntry.application_id == application.id,
        )
    )
    return {
        "status": application.status,
        "waiting_list_id": str(waiting.id) if waiting else None,
        "waiting_list_position": waiting.position if waiting else None,
        "waiting_list_status": waiting.status if waiting else None,
    }


def run_analysis(
    session: Session,
    ctx: OrganisationContext,
    *,
    application_id: uuid.UUID,
    force: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    _guard(ctx, lambda: analysis_access.require_run(ctx), application_id=application_id)
    settings = settings or get_settings()
    application = _guard(
        ctx, lambda: analysis_access.load_application(session, ctx, application_id), application_id=application_id
    )
    before = _snapshot_application(session, application)
    evaluated = evaluate_application(session, application=application)
    fingerprint = evaluated["source_fingerprint"]
    existing = _latest(session, ctx.organisation_id, application.id)
    if existing and existing.source_fingerprint == fingerprint and not force:
        return {
            **_public(existing, _load_findings(session, existing.id), current_fingerprint=fingerprint),
            "idempotent": True,
        }

    record_event(
        session,
        action=audit_events.AI_HOUSING_APPLICATION_REQUESTED,
        resource_type="housing_application",
        resource_id=str(application.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Housing application analysis requested",
        metadata={"application_id": str(application.id), "force": force},
        raise_on_error=False,
    )
    record_event(
        session,
        action=audit_events.AI_HOUSING_APPLICATION_CHECKLIST_COMPLETED,
        resource_type="housing_application",
        resource_id=str(application.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Housing application checklist evaluation completed",
        metadata={"finding_count": len(evaluated["findings"]), "counts": evaluated["counts"]},
        raise_on_error=False,
    )

    ai_status = "not_needed"
    ai_error = None
    generation_method = "structured_heuristic"
    provider = "heuristic"
    model_id = "structured_heuristic_v1"
    prompt_id = "hmore.housing_application_analysis.v1"
    prompt_version = "1.0.0"
    narrative = heuristic_gap_narrative(evaluated["findings"], application_reference=application.reference_number)
    needs_ai = any(
        item["outcome"] in {"missing", "incomplete", "needs_review", "not_performed"}
        for item in evaluated["findings"]
    )
    if needs_ai:
        if (settings.ai_service_base_url or "").strip():
            try:
                raw = explain_gaps(
                    settings,
                    organisation_id=ctx.organisation_id,
                    user_id=ctx.user_id,
                    role=ctx.role.value,
                    findings=evaluated["findings"],
                    application_reference=application.reference_number,
                )
                payload = (raw.get("result") or {}).get("analysis") or {}
                narrative = validate_ai_narrative(str(payload.get("gap_narrative") or ""))
                ai_status = "completed"
                generation_method = "llm"
                provider = (raw.get("result") or {}).get("provider")
                model_id = (raw.get("result") or {}).get("model_id")
                prompt_id = (raw.get("result") or {}).get("prompt_id") or prompt_id
                prompt_version = (raw.get("result") or {}).get("prompt_version") or prompt_version
                record_event(
                    session,
                    action=audit_events.AI_HOUSING_APPLICATION_AI_COMPLETED,
                    resource_type="housing_application",
                    resource_id=str(application.id),
                    organisation_id=ctx.organisation_id,
                    actor_user_id=ctx.user_id,
                    actor_role=ctx.role.value,
                    outcome=AuditOutcome.SUCCESS,
                    summary="Housing application gap narrative completed",
                    metadata={"application_id": str(application.id)},
                    raise_on_error=False,
                )
            except HTTPException as exc:
                if exc.status_code == 402:
                    ai_status = "skipped_budget"
                    ai_error = "ai_budget_exceeded"
                else:
                    ai_status = "failed"
                    ai_error = "ai_unavailable"
                narrative = heuristic_gap_narrative(
                    evaluated["findings"], application_reference=application.reference_number
                )
                record_event(
                    session,
                    action=audit_events.AI_HOUSING_APPLICATION_AI_SKIPPED
                    if ai_status.startswith("skipped")
                    else audit_events.AI_HOUSING_APPLICATION_AI_FAILED,
                    resource_type="housing_application",
                    resource_id=str(application.id),
                    organisation_id=ctx.organisation_id,
                    actor_user_id=ctx.user_id,
                    actor_role=ctx.role.value,
                    outcome=AuditOutcome.DENIED if exc.status_code == 402 else AuditOutcome.FAILURE,
                    summary="Housing application gap narrative did not complete",
                    metadata={"ai_status": ai_status},
                    raise_on_error=False,
                )
            except ValueError:
                ai_status = "failed"
                ai_error = "invalid_ai_output"
                narrative = heuristic_gap_narrative(
                    evaluated["findings"], application_reference=application.reference_number
                )
                record_event(
                    session,
                    action=audit_events.AI_HOUSING_APPLICATION_AI_FAILED,
                    resource_type="housing_application",
                    resource_id=str(application.id),
                    organisation_id=ctx.organisation_id,
                    actor_user_id=ctx.user_id,
                    actor_role=ctx.role.value,
                    outcome=AuditOutcome.FAILURE,
                    summary="Housing application AI narrative rejected",
                    metadata={"ai_status": ai_status},
                    raise_on_error=False,
                )
        else:
            if settings.is_production:
                ai_status = "skipped_unavailable"
                ai_error = "ai_not_configured"
            else:
                ai_status = "heuristic"
                generation_method = "structured_heuristic"

    row = HousingApplicationAnalysis(
        id=uuid.uuid4(),
        organisation_id=ctx.organisation_id,
        application_id=application.id,
        version_number=_next_version(session, ctx.organisation_id, application.id),
        source_fingerprint=fingerprint,
        status="pending_review",
        checklist_summary_json=evaluated["counts"],
        gap_narrative=narrative,
        source_refs_json=evaluated["sources"],
        requested_by_user_id=ctx.user_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider,
        model_id=model_id,
        generation_method=generation_method,
        ai_status=ai_status,
        ai_error=ai_error,
        generated_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    finding_rows: list[HousingApplicationAnalysisFinding] = []
    for item in evaluated["findings"]:
        finding = HousingApplicationAnalysisFinding(
            id=uuid.uuid4(),
            organisation_id=ctx.organisation_id,
            analysis_id=row.id,
            code=item["code"],
            source=item["source"],
            outcome=item["outcome"],
            title=item["title"][:200],
            detail=item["detail"],
            recommended_action=item.get("recommended_action"),
            related_checklist_item_id=uuid.UUID(item["related_checklist_item_id"])
            if item.get("related_checklist_item_id")
            else None,
            related_file_id=uuid.UUID(item["related_file_id"]) if item.get("related_file_id") else None,
            needs_human_verification=bool(item.get("needs_human_verification")),
            review_status="pending",
        )
        session.add(finding)
        finding_rows.append(finding)
    session.flush()

    session.refresh(application)
    after = _snapshot_application(session, application)
    if after != before:
        raise HTTPException(status_code=500, detail="Analysis must not change the housing application")
    saved_action = (
        audit_events.AI_HOUSING_APPLICATION_REGENERATED
        if force
        else audit_events.AI_HOUSING_APPLICATION_CHECKLIST_COMPLETED
    )
    record_event(
        session,
        action=saved_action,
        resource_type="housing_application_analysis",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Housing application analysis saved",
        metadata={"version_number": row.version_number, "ai_status": ai_status},
        raise_on_error=False,
    )
    return {
        **_public(row, finding_rows, current_fingerprint=fingerprint),
        "idempotent": False,
        "application_status_unchanged": application.status,
        "waiting_list_unchanged": True,
    }


def get_analysis(session: Session, ctx: OrganisationContext, analysis_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: analysis_access.require_read(ctx), application_id=None)
    row = session.get(HousingApplicationAnalysis, analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Housing application analysis not found")
    try:
        assert_same_organisation(ctx, row.organisation_id)
    except HTTPException as exc:
        if exc.status_code == 403:
            _denied(ctx, application_id=row.application_id)
        raise
    application = _guard(
        ctx, lambda: analysis_access.load_application(session, ctx, row.application_id), application_id=row.application_id
    )
    current = evaluate_application(session, application=application)["source_fingerprint"]
    return _public(row, _load_findings(session, row.id), current_fingerprint=current)


def list_analyses(session: Session, ctx: OrganisationContext, application_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: analysis_access.require_read(ctx), application_id=application_id)
    _guard(ctx, lambda: analysis_access.load_application(session, ctx, application_id), application_id=application_id)
    rows = list(
        session.scalars(
            select(HousingApplicationAnalysis)
            .where(
                HousingApplicationAnalysis.organisation_id == ctx.organisation_id,
                HousingApplicationAnalysis.application_id == application_id,
            )
            .order_by(HousingApplicationAnalysis.version_number.desc())
        )
    )
    return {"items": [_public(row, _load_findings(session, row.id)) for row in rows]}


def decide_finding(
    session: Session,
    ctx: OrganisationContext,
    finding_id: uuid.UUID,
    *,
    decision: str,
    review_comment: str | None,
) -> dict[str, Any]:
    _guard(ctx, lambda: analysis_access.require_review(ctx))
    finding = session.get(HousingApplicationAnalysisFinding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    assert_same_organisation(ctx, finding.organisation_id)
    analysis = session.get(HousingApplicationAnalysis, finding.analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Housing application analysis not found")
    application = _guard(
        ctx,
        lambda: analysis_access.load_application(session, ctx, analysis.application_id),
        application_id=analysis.application_id,
    )
    before = _snapshot_application(session, application)
    finding.review_status = "confirmed" if decision == "confirm" else "dismissed"
    finding.reviewed_by_user_id = ctx.user_id
    finding.reviewed_at = datetime.now(timezone.utc)
    finding.review_comment = review_comment
    session.flush()
    session.refresh(application)
    if _snapshot_application(session, application) != before:
        raise HTTPException(status_code=500, detail="Review must not change the housing application")
    record_event(
        session,
        action=audit_events.AI_HOUSING_APPLICATION_FINDING_CONFIRMED
        if decision == "confirm"
        else audit_events.AI_HOUSING_APPLICATION_FINDING_DISMISSED,
        resource_type="housing_application_analysis_finding",
        resource_id=str(finding.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Housing application analysis finding reviewed",
        metadata={"analysis_id": str(analysis.id), "code": finding.code},
        raise_on_error=False,
    )
    return get_analysis(session, ctx, analysis.id)


def review_analysis(
    session: Session,
    ctx: OrganisationContext,
    analysis_id: uuid.UUID,
    *,
    review_comment: str | None,
) -> dict[str, Any]:
    _guard(ctx, lambda: analysis_access.require_review(ctx), application_id=None)
    row = session.get(HousingApplicationAnalysis, analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Housing application analysis not found")
    assert_same_organisation(ctx, row.organisation_id)
    application = analysis_access.load_application(session, ctx, row.application_id)
    before = _snapshot_application(session, application)
    row.status = "reviewed"
    row.reviewed_by_user_id = ctx.user_id
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_comment = review_comment
    session.flush()
    session.refresh(application)
    if _snapshot_application(session, application) != before:
        raise HTTPException(status_code=500, detail="Review must not change the housing application")
    record_event(
        session,
        action=audit_events.AI_HOUSING_APPLICATION_REVIEWED,
        resource_type="housing_application_analysis",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Housing application analysis marked reviewed",
        metadata={"application_id": str(application.id)},
        raise_on_error=False,
    )
    return get_analysis(session, ctx, row.id)
