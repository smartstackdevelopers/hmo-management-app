"""F3.4 Notes Analysis orchestration — caseload-gated, human-reviewed."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.notes_analysis import DailyLogAiAnalysis, DailyLogAiSuggestion
from app.db.models.support_ops import DailyLog
from app.notes_analysis import access as na_access
from app.notes_analysis.ai_client import execute_notes_analysis_workflow
from app.notes_analysis.heuristic import build_heuristic_analysis
from app.notes_analysis.versioning import note_payload_for_ai, source_note_version
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation


def _analysis_dict(a: DailyLogAiAnalysis, *, include_suggestions: list[DailyLogAiSuggestion] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(a.id),
        "organisation_id": str(a.organisation_id),
        "daily_log_id": str(a.daily_log_id),
        "tenant_id": str(a.tenant_id),
        "source_note_version": a.source_note_version,
        "status": a.status,
        "generation_kind": a.generation_kind,
        "generation_method": a.generation_method,
        "ai_generated": True,
        "summary": a.summary_text,
        "key_observations": a.key_observations_json or [],
        "missing_details": a.missing_details_json or [],
        "suggested_actions": a.suggested_actions_json or [],
        "uncertainty_notes": a.uncertainty_notes,
        "source_refs": a.source_refs_json or {},
        "prompt_id": a.prompt_id,
        "prompt_version": a.prompt_version,
        "provider": a.provider,
        "model_id": a.model_id,
        "request_id": a.request_id,
        "batch_job_id": a.batch_job_id,
        "generated_at": a.generated_at.isoformat() if a.generated_at else None,
        "reviewed_by_user_id": str(a.reviewed_by_user_id) if a.reviewed_by_user_id else None,
        "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
        "review_comment": a.review_comment,
        "error_message": a.error_message,
    }
    if include_suggestions is not None:
        data["suggestions"] = [_suggestion_dict(s) for s in include_suggestions]
    return data


def _suggestion_dict(s: DailyLogAiSuggestion) -> dict[str, Any]:
    return {
        "id": str(s.id),
        "analysis_id": str(s.analysis_id),
        "daily_log_id": str(s.daily_log_id),
        "kind": s.kind,
        "title": s.title,
        "body": s.edited_body or s.body,
        "original_body": s.body,
        "rationale": s.rationale,
        "source_excerpt": s.source_excerpt,
        "is_interpretation": s.is_interpretation,
        "review_status": s.review_status,
        "reviewed_by_user_id": str(s.reviewed_by_user_id) if s.reviewed_by_user_id else None,
        "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
        "reviewer_note": s.reviewer_note,
        "sort_order": s.sort_order,
    }


def _get_log(session: Session, ctx: OrganisationContext, log_id: uuid.UUID) -> DailyLog:
    log = session.get(DailyLog, log_id)
    if log is None or log.status == "voided":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily note not found")
    assert_same_organisation(ctx, log.organisation_id)
    na_access.assert_note_tenant_access(session, ctx, log.tenant_id)
    return log


def _find_existing(
    session: Session,
    *,
    daily_log_id: uuid.UUID,
    version: str,
    generation_kind: str,
) -> DailyLogAiAnalysis | None:
    return session.scalars(
        select(DailyLogAiAnalysis).where(
            DailyLogAiAnalysis.daily_log_id == daily_log_id,
            DailyLogAiAnalysis.source_note_version == version,
            DailyLogAiAnalysis.generation_kind == generation_kind,
            DailyLogAiAnalysis.status != "failed",
        )
    ).first()


def run_analysis(
    session: Session,
    ctx: OrganisationContext,
    *,
    daily_log_id: uuid.UUID,
    force: bool = False,
    generation_kind: str = "on_demand",
    batch_job_id: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    na_access.require_notes_analysis_run(ctx)
    from app.ai_feature_flags.service import require_feature_available
    from app.ai_usage.features import FEATURE_NOTES_ANALYSIS

    require_feature_available(session, ctx, FEATURE_NOTES_ANALYSIS)
    settings = settings or get_settings()
    log = _get_log(session, ctx, daily_log_id)
    version = source_note_version(log)

    existing = _find_existing(
        session, daily_log_id=log.id, version=version, generation_kind=generation_kind
    )
    if existing and not force:
        suggestions = list(
            session.scalars(
                select(DailyLogAiSuggestion)
                .where(DailyLogAiSuggestion.analysis_id == existing.id)
                .order_by(DailyLogAiSuggestion.sort_order)
            )
        )
        return {
            **_analysis_dict(existing, include_suggestions=suggestions),
            "idempotent": True,
            "stale": False,
        }

    record_event(
        session,
        action=audit_events.AI_NOTES_ANALYSIS_RUN,
        resource_type="daily_log_ai_analysis",
        resource_id=str(log.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Notes analysis requested",
        metadata={"daily_log_id": str(log.id), "source_note_version": version, "generation_kind": generation_kind},
        raise_on_error=False,
    )

    note_payload = note_payload_for_ai(log)
    try:
        if (getattr(settings, "ai_service_base_url", "") or "").strip():
            raw = execute_notes_analysis_workflow(
                settings,
                organisation_id=ctx.organisation_id,
                user_id=ctx.user_id,
                role=ctx.role.value,
                note_payload=note_payload,
            )
            result_block = raw.get("result") or {}
            request_id = raw.get("request_id")
        else:
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI service is not configured",
                )
            result_block = build_heuristic_analysis(note_payload)
            request_id = str(uuid.uuid4())
    except HTTPException as exc:
        if exc.status_code == status.HTTP_402_PAYMENT_REQUIRED:
            record_event(
                session,
                action=audit_events.AI_NOTES_ANALYSIS_FAILED,
                resource_type="daily_log",
                resource_id=str(log.id),
                organisation_id=ctx.organisation_id,
                actor_user_id=ctx.user_id,
                actor_role=ctx.role.value,
                outcome=AuditOutcome.DENIED,
                summary="Notes analysis rejected — AI budget exhausted",
                metadata={"daily_log_id": str(log.id)},
                raise_on_error=False,
            )
        raise

    analysis_payload = result_block.get("analysis") or {}
    if not analysis_payload.get("summary"):
        failed = DailyLogAiAnalysis(
            id=uuid.uuid4(),
            organisation_id=ctx.organisation_id,
            daily_log_id=log.id,
            tenant_id=log.tenant_id,
            triggered_by_user_id=ctx.user_id,
            source_note_version=version,
            status="failed",
            generation_kind=generation_kind,
            generation_method=result_block.get("generation_method") or "llm",
            error_message="AI output missing required summary",
            request_id=request_id,
            batch_job_id=batch_job_id,
            generated_at=datetime.now(timezone.utc),
        )
        session.add(failed)
        session.flush()
        record_event(
            session,
            action=audit_events.AI_NOTES_ANALYSIS_FAILED,
            resource_type="daily_log_ai_analysis",
            resource_id=str(failed.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Notes analysis failed validation",
            metadata={"daily_log_id": str(log.id)},
            raise_on_error=False,
        )
        raise HTTPException(status_code=422, detail="AI output failed validation")

    # Force re-run updates the same version row (unique constraint) and supersedes old suggestions.
    if existing and force:
        for old in session.scalars(
            select(DailyLogAiSuggestion).where(DailyLogAiSuggestion.analysis_id == existing.id)
        ):
            old.review_status = "superseded"
        analysis = existing
        analysis.triggered_by_user_id = ctx.user_id
        analysis.request_id = request_id
        analysis.prompt_id = result_block.get("prompt_id")
        analysis.prompt_version = result_block.get("prompt_version")
        analysis.provider = result_block.get("provider")
        analysis.model_id = result_block.get("model_id")
        analysis.generation_method = (
            result_block.get("generation_method") or analysis_payload.get("generation_method") or "llm"
        )
        analysis.status = "pending_review"
        analysis.summary_text = analysis_payload.get("summary")
        analysis.key_observations_json = list(analysis_payload.get("key_observations") or [])
        analysis.missing_details_json = list(analysis_payload.get("missing_details") or [])
        analysis.suggested_actions_json = list(analysis_payload.get("suggested_actions") or [])
        analysis.uncertainty_notes = analysis_payload.get("uncertainty_notes")
        analysis.source_refs_json = {
            "daily_log_id": str(log.id),
            "source_note_version": version,
            "log_date": log.log_date.isoformat() if log.log_date else None,
        }
        analysis.batch_job_id = batch_job_id
        analysis.generated_at = datetime.now(timezone.utc)
        analysis.reviewed_by_user_id = None
        analysis.reviewed_at = None
        analysis.review_comment = None
        analysis.error_message = None
        session.flush()
    else:
        analysis = DailyLogAiAnalysis(
            id=uuid.uuid4(),
            organisation_id=ctx.organisation_id,
            daily_log_id=log.id,
            tenant_id=log.tenant_id,
            triggered_by_user_id=ctx.user_id,
            source_note_version=version,
            workflow_id="notes_analysis",
            feature_id="ai.agent.notes_analysis",
            request_id=request_id,
            prompt_id=result_block.get("prompt_id"),
            prompt_version=result_block.get("prompt_version"),
            provider=result_block.get("provider"),
            model_id=result_block.get("model_id"),
            generation_kind=generation_kind,
            generation_method=result_block.get("generation_method")
            or analysis_payload.get("generation_method")
            or "llm",
            status="pending_review",
            summary_text=analysis_payload.get("summary"),
            key_observations_json=list(analysis_payload.get("key_observations") or []),
            missing_details_json=list(analysis_payload.get("missing_details") or []),
            suggested_actions_json=list(analysis_payload.get("suggested_actions") or []),
            uncertainty_notes=analysis_payload.get("uncertainty_notes"),
            source_refs_json={
                "daily_log_id": str(log.id),
                "source_note_version": version,
                "log_date": log.log_date.isoformat() if log.log_date else None,
            },
            batch_job_id=batch_job_id,
            generated_at=datetime.now(timezone.utc),
        )
        session.add(analysis)
        session.flush()

    suggestions: list[DailyLogAiSuggestion] = []
    order = 0
    for item in analysis.missing_details_json:
        suggestions.append(
            DailyLogAiSuggestion(
                id=uuid.uuid4(),
                organisation_id=ctx.organisation_id,
                analysis_id=analysis.id,
                daily_log_id=log.id,
                kind="missing_detail",
                title=str(item.get("title") or "Missing detail")[:255],
                body=str(item.get("body") or ""),
                rationale=item.get("rationale"),
                source_excerpt=item.get("source_excerpt"),
                is_interpretation=bool(item.get("is_interpretation", True)),
                review_status="pending",
                sort_order=order,
            )
        )
        order += 1
    for item in analysis.suggested_actions_json:
        suggestions.append(
            DailyLogAiSuggestion(
                id=uuid.uuid4(),
                organisation_id=ctx.organisation_id,
                analysis_id=analysis.id,
                daily_log_id=log.id,
                kind="next_action",
                title=str(item.get("title") or "Suggested action")[:255],
                body=str(item.get("body") or ""),
                rationale=item.get("rationale"),
                source_excerpt=item.get("source_excerpt"),
                is_interpretation=bool(item.get("is_interpretation", True)),
                review_status="pending",
                sort_order=order,
            )
        )
        order += 1
    for obs in analysis.key_observations_json:
        suggestions.append(
            DailyLogAiSuggestion(
                id=uuid.uuid4(),
                organisation_id=ctx.organisation_id,
                analysis_id=analysis.id,
                daily_log_id=log.id,
                kind="observation",
                title="Key observation",
                body=str(obs),
                rationale="Extracted observation for human review",
                source_excerpt=None,
                is_interpretation=True,
                review_status="pending",
                sort_order=order,
            )
        )
        order += 1
    session.add_all(suggestions)
    session.flush()

    record_event(
        session,
        action=audit_events.AI_NOTES_ANALYSIS_COMPLETE,
        resource_type="daily_log_ai_analysis",
        resource_id=str(analysis.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Notes analysis completed — pending human review",
        metadata={
            "daily_log_id": str(log.id),
            "suggestion_count": len(suggestions),
            "generation_method": analysis.generation_method,
        },
        raise_on_error=False,
    )
    # F3.14 — preserve genuine source refs; confidence remains unavailable (no calibrated score).
    from app.ai_transparency.service import attach_transparency, record_local_activity

    if not attach_transparency(
        session,
        request_id=request_id,
        organisation_id=ctx.organisation_id,
        source_refs=analysis.source_refs_json,
        confidence_kind="unavailable",
        human_approval_status="pending",
        output_ref={"type": "daily_log_ai_analysis", "id": str(analysis.id)},
        operation_type="notes_analysis",
    ):
        record_local_activity(
            session,
            organisation_id=ctx.organisation_id,
            request_id=request_id,
            feature_id="ai.agent.notes_analysis",
            workflow_id="notes_analysis",
            user_id=ctx.user_id,
            execution_status="completed",
            prompt_id=analysis.prompt_id,
            prompt_version=analysis.prompt_version,
            provider=analysis.provider,
            model_id=analysis.model_id,
            source_refs=analysis.source_refs_json,
            confidence_kind="unavailable",
            human_approval_status="pending",
            output_ref={"type": "daily_log_ai_analysis", "id": str(analysis.id)},
            operation_type="notes_analysis",
        )
    return {
        **_analysis_dict(analysis, include_suggestions=suggestions),
        "idempotent": False,
        "stale": False,
    }


def get_analysis(session: Session, ctx: OrganisationContext, analysis_id: uuid.UUID) -> dict[str, Any]:
    na_access.require_notes_analysis_read(ctx)
    analysis = session.get(DailyLogAiAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    assert_same_organisation(ctx, analysis.organisation_id)
    na_access.assert_note_tenant_access(session, ctx, analysis.tenant_id)
    log = session.get(DailyLog, analysis.daily_log_id)
    stale = False
    if log is not None:
        stale = source_note_version(log) != analysis.source_note_version
    suggestions = list(
        session.scalars(
            select(DailyLogAiSuggestion)
            .where(DailyLogAiSuggestion.analysis_id == analysis.id)
            .order_by(DailyLogAiSuggestion.sort_order)
        )
    )
    return {
        **_analysis_dict(analysis, include_suggestions=suggestions),
        "stale": stale,
        "source_note": {
            "id": str(log.id) if log else None,
            "summary": log.summary if log else None,
            "notes": log.notes if log else None,
            "follow_up_required": log.follow_up_required if log else None,
            "next_action": log.next_action if log else None,
            "log_date": log.log_date.isoformat() if log and log.log_date else None,
            "status": log.status if log else None,
            "current_source_note_version": source_note_version(log) if log else None,
        },
    }


def list_inbox(session: Session, ctx: OrganisationContext, *, page: int = 1, page_size: int = 50) -> dict[str, Any]:
    na_access.require_notes_analysis_inbox(ctx)
    stmt = (
        select(DailyLogAiAnalysis)
        .where(
            DailyLogAiAnalysis.organisation_id == ctx.organisation_id,
            DailyLogAiAnalysis.status == "pending_review",
        )
        .order_by(DailyLogAiAnalysis.generated_at.desc())
    )
    # Support workers only see analyses for assigned tenants via per-row check after fetch.
    rows = list(session.scalars(stmt.offset((page - 1) * page_size).limit(page_size * 3)))
    items = []
    for a in rows:
        try:
            na_access.assert_note_tenant_access(session, ctx, a.tenant_id)
        except HTTPException:
            continue
        items.append(
            {
                "source_type": "notes_analysis",
                "source_id": str(a.id),
                "reference": f"NA-{str(a.id)[:8]}",
                "title": "AI notes analysis pending review",
                "status": a.status,
                "related_url_path": f"/dashboard/notes-analysis/{a.id}",
                "daily_log_id": str(a.daily_log_id),
                "tenant_id": str(a.tenant_id),
                "generated_at": a.generated_at.isoformat() if a.generated_at else None,
                "ai_generated": True,
            }
        )
        if len(items) >= page_size:
            break
    return {"page": page, "page_size": page_size, "items": items}


def decide_suggestion(
    session: Session,
    ctx: OrganisationContext,
    suggestion_id: uuid.UUID,
    *,
    decision: str,
    reviewer_note: str | None = None,
    edited_body: str | None = None,
) -> dict[str, Any]:
    na_access.require_notes_analysis_review(ctx)
    suggestion = session.get(DailyLogAiSuggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    assert_same_organisation(ctx, suggestion.organisation_id)
    analysis = session.get(DailyLogAiAnalysis, suggestion.analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    na_access.assert_note_tenant_access(session, ctx, analysis.tenant_id)

    log = session.get(DailyLog, suggestion.daily_log_id)
    if log is None or source_note_version(log) != analysis.source_note_version:
        raise HTTPException(
            status_code=409,
            detail="Suggestion is stale — source note changed; regenerate analysis before applying",
        )
    if suggestion.review_status != "pending":
        raise HTTPException(status_code=409, detail="Suggestion already decided")

    now = datetime.now(timezone.utc)
    if decision == "approve":
        suggestion.review_status = "approved"
        if edited_body:
            suggestion.edited_body = edited_body
        action = audit_events.AI_NOTES_ANALYSIS_SUGGESTION_APPROVE
    elif decision == "reject":
        suggestion.review_status = "rejected"
        action = audit_events.AI_NOTES_ANALYSIS_SUGGESTION_REJECT
    else:
        suggestion.review_status = "dismissed"
        action = audit_events.AI_NOTES_ANALYSIS_SUGGESTION_REJECT

    suggestion.reviewed_by_user_id = ctx.user_id
    suggestion.reviewed_at = now
    suggestion.reviewer_note = reviewer_note
    session.flush()

    # Never auto-mutate the daily log — approval records human intent only.
    record_event(
        session,
        action=action,
        resource_type="daily_log_ai_suggestion",
        resource_id=str(suggestion.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Notes analysis suggestion {decision}",
        metadata={"analysis_id": str(analysis.id), "kind": suggestion.kind},
        raise_on_error=False,
    )
    _refresh_analysis_status(session, analysis)
    return _suggestion_dict(suggestion)


def review_analysis(
    session: Session,
    ctx: OrganisationContext,
    analysis_id: uuid.UUID,
    *,
    decision: str,
    review_comment: str | None = None,
) -> dict[str, Any]:
    na_access.require_notes_analysis_review(ctx)
    analysis = session.get(DailyLogAiAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    assert_same_organisation(ctx, analysis.organisation_id)
    na_access.assert_note_tenant_access(session, ctx, analysis.tenant_id)
    if analysis.status not in {"pending_review", "partially_approved"}:
        raise HTTPException(status_code=409, detail="Analysis is not awaiting review")

    mapping = {
        "approve": "approved",
        "partially_approve": "partially_approved",
        "reject": "rejected",
    }
    analysis.status = mapping[decision]
    analysis.reviewed_by_user_id = ctx.user_id
    analysis.reviewed_at = datetime.now(timezone.utc)
    analysis.review_comment = review_comment
    session.flush()
    record_event(
        session,
        action=audit_events.AI_NOTES_ANALYSIS_REVIEWED,
        resource_type="daily_log_ai_analysis",
        resource_id=str(analysis.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Notes analysis marked {analysis.status}",
        metadata={"decision": decision},
        raise_on_error=False,
    )
    return get_analysis(session, ctx, analysis_id)


def _refresh_analysis_status(session: Session, analysis: DailyLogAiAnalysis) -> None:
    rows = list(
        session.scalars(select(DailyLogAiSuggestion).where(DailyLogAiSuggestion.analysis_id == analysis.id))
    )
    if not rows:
        return
    statuses = {r.review_status for r in rows}
    if statuses <= {"approved", "applied"}:
        analysis.status = "approved"
    elif "pending" in statuses and statuses & {"approved", "rejected", "dismissed", "applied"}:
        analysis.status = "partially_approved"
    elif statuses <= {"rejected", "dismissed", "superseded"}:
        analysis.status = "rejected"


def list_eligible_for_batch(session: Session, ctx: OrganisationContext, *, limit: int = 50) -> dict[str, Any]:
    """Select active logs without an analysis for the current content version."""
    na_access.require_notes_analysis_run(ctx)
    logs = list(
        session.scalars(
            select(DailyLog)
            .where(
                DailyLog.organisation_id == ctx.organisation_id,
                DailyLog.status == "active",
            )
            .order_by(DailyLog.log_date.desc())
            .limit(limit * 3)
        )
    )
    eligible = []
    for log in logs:
        try:
            na_access.assert_note_tenant_access(session, ctx, log.tenant_id)
        except HTTPException:
            continue
        version = source_note_version(log)
        existing = _find_existing(
            session, daily_log_id=log.id, version=version, generation_kind="batch"
        )
        on_demand = _find_existing(
            session, daily_log_id=log.id, version=version, generation_kind="on_demand"
        )
        if existing or on_demand:
            continue
        eligible.append(
            {
                "daily_log_id": str(log.id),
                "tenant_id": str(log.tenant_id),
                "source_note_version": version,
                "log_date": log.log_date.isoformat() if log.log_date else None,
            }
        )
        if len(eligible) >= limit:
            break
    return {"items": eligible, "count": len(eligible)}


def run_batch_for_org(
    session: Session,
    ctx: OrganisationContext,
    *,
    limit: int = 50,
    settings: Settings | None = None,
) -> dict[str, Any]:
    eligible = list_eligible_for_batch(session, ctx, limit=limit)["items"]
    results = []
    for item in eligible:
        try:
            out = run_analysis(
                session,
                ctx,
                daily_log_id=uuid.UUID(item["daily_log_id"]),
                generation_kind="batch",
                batch_job_id=str(uuid.uuid4()),
                settings=settings,
            )
            results.append({"daily_log_id": item["daily_log_id"], "status": "ok", "analysis_id": out["id"]})
        except HTTPException as exc:
            results.append(
                {
                    "daily_log_id": item["daily_log_id"],
                    "status": "error",
                    "detail": exc.detail,
                    "http_status": exc.status_code,
                }
            )
    record_event(
        session,
        action=audit_events.AI_NOTES_ANALYSIS_BATCH,
        resource_type="notes_analysis_batch",
        resource_id=str(ctx.organisation_id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Notes analysis batch completed",
        metadata={"processed": len(results)},
        raise_on_error=False,
    )
    return {"processed": len(results), "results": results}
