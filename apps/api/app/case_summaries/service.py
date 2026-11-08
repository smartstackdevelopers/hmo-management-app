"""F3.5 case summary generation, versioning, and human review."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event, record_event_independent
from app.case_summaries import access as case_access
from app.case_summaries.ai_client import execute_case_summary
from app.case_summaries.compose import compose_case_summary, source_fingerprint
from app.case_summaries.sources import collect_case_packet
from app.core.config import Settings, get_settings
from app.db.models.case_summaries import CaseSummary
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation


def _public(row: CaseSummary, *, current_fingerprint: str | None = None) -> dict[str, Any]:
    stale = current_fingerprint is not None and current_fingerprint != row.source_fingerprint
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "tenant_id": str(row.tenant_id),
        "version_number": row.version_number,
        "status": row.status,
        "ai_generated": True,
        "generation_method": row.generation_method,
        "sections": row.sections_json or {},
        "missing_information": row.missing_information_json or [],
        "recorded_concerns": row.recorded_concerns_json or [],
        "source_refs": row.source_refs_json or [],
        "covered_from": row.covered_from,
        "covered_to": row.covered_to,
        "uncertainty_notes": row.uncertainty_notes,
        "prompt_id": row.prompt_id,
        "prompt_version": row.prompt_version,
        "provider": row.provider,
        "model_id": row.model_id,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        "requested_by_user_id": str(row.requested_by_user_id) if row.requested_by_user_id else None,
        "reviewed_by_user_id": str(row.reviewed_by_user_id) if row.reviewed_by_user_id else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "review_comment": row.review_comment,
        "stale": stale,
        "source_fingerprint": row.source_fingerprint,
    }


def _latest(session: Session, organisation_id: uuid.UUID, tenant_id: uuid.UUID) -> CaseSummary | None:
    return session.scalars(
        select(CaseSummary)
        .where(CaseSummary.organisation_id == organisation_id, CaseSummary.tenant_id == tenant_id)
        .order_by(CaseSummary.version_number.desc())
        .limit(1)
    ).first()


def _next_version(session: Session, organisation_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
    current = session.scalar(
        select(func.max(CaseSummary.version_number)).where(
            CaseSummary.organisation_id == organisation_id,
            CaseSummary.tenant_id == tenant_id,
        )
    )
    return int(current or 0) + 1


def _audit_denied(ctx: OrganisationContext, *, tenant_id: uuid.UUID | None = None, summary_id: uuid.UUID | None = None) -> None:
    record_event_independent(
        action=audit_events.AI_CASE_SUMMARY_DENIED,
        resource_type="case_summary" if summary_id else "tenant",
        resource_id=str(summary_id or tenant_id or ""),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.DENIED,
        summary="Case summary access denied",
        metadata={
            "tenant_id": str(tenant_id) if tenant_id else None,
            "summary_id": str(summary_id) if summary_id else None,
        },
    )


def _guard(ctx: OrganisationContext, fn, *, tenant_id: uuid.UUID | None = None, summary_id: uuid.UUID | None = None):
    try:
        return fn()
    except HTTPException as exc:
        if exc.status_code == 403:
            _audit_denied(ctx, tenant_id=tenant_id, summary_id=summary_id)
        raise


def _accept_result(result: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    sections = result.get("sections") or {}
    if not isinstance(sections, dict) or not str(sections.get("overview") or "").strip():
        raise HTTPException(status_code=422, detail="AI output failed validation")
    for key in ("background", "events", "recent_support", "needs_and_goals", "outstanding_actions", "upcoming"):
        if not str(sections.get(key) or "").strip():
            raise HTTPException(status_code=422, detail="AI output failed validation")
    allowed = {str(item.get("id")) for item in (packet.get("sources") or []) if item.get("id")}
    concerns = result.get("recorded_concerns") or []
    if not isinstance(concerns, list):
        raise HTTPException(status_code=422, detail="AI output failed validation")
    for concern in concerns:
        if not isinstance(concern, dict):
            raise HTTPException(status_code=422, detail="AI output failed validation")
        if concern.get("explicitly_recorded") is not True:
            raise HTTPException(status_code=422, detail="AI output failed validation")
        if str(concern.get("source_id") or "") not in allowed:
            raise HTTPException(status_code=422, detail="AI output failed validation")
    method = result.get("generation_method") or "structured_heuristic"
    if method not in {"llm", "structured_heuristic"}:
        raise HTTPException(status_code=422, detail="AI output failed validation")
    return result


def generate_summary(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: uuid.UUID,
    force: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    _guard(ctx, lambda: case_access.require_run(ctx), tenant_id=tenant_id)
    from app.ai_feature_flags.service import require_feature_available
    from app.ai_usage.features import FEATURE_CASE_SUMMARY

    require_feature_available(session, ctx, FEATURE_CASE_SUMMARY)
    settings = settings or get_settings()
    tenant = _guard(ctx, lambda: case_access.assert_case_access(session, ctx, tenant_id), tenant_id=tenant_id)
    packet = collect_case_packet(session, organisation_id=ctx.organisation_id, tenant=tenant)
    fingerprint = source_fingerprint(packet)
    existing = _latest(session, ctx.organisation_id, tenant.id)
    if existing and existing.source_fingerprint == fingerprint and existing.status != "failed" and not force:
        return {**_public(existing, current_fingerprint=fingerprint), "idempotent": True, "regenerated": False}

    record_event(
        session,
        action=audit_events.AI_CASE_SUMMARY_REQUESTED,
        resource_type="case_summary",
        resource_id=str(tenant.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Case summary requested",
        metadata={"tenant_id": str(tenant.id), "source_count": len(packet.get("sources") or []), "force": force},
        raise_on_error=False,
    )

    try:
        if (settings.ai_service_base_url or "").strip():
            raw = execute_case_summary(
                settings,
                organisation_id=ctx.organisation_id,
                user_id=ctx.user_id,
                role=ctx.role.value,
                packet=packet,
            )
            result = (raw.get("result") or {}).get("summary") or {}
            request_id = raw.get("request_id")
            prompt_id = (raw.get("result") or {}).get("prompt_id")
            prompt_version = (raw.get("result") or {}).get("prompt_version")
            provider = (raw.get("result") or {}).get("provider")
            model_id = (raw.get("result") or {}).get("model_id")
        else:
            if settings.is_production:
                raise HTTPException(status_code=503, detail="AI service is not configured")
            result = compose_case_summary(packet)
            request_id = str(uuid.uuid4())
            prompt_id = "hmore.case_summary.v1"
            prompt_version = "1.0.0"
            provider = "heuristic"
            model_id = "structured_heuristic_v1"
    except HTTPException as exc:
        if exc.status_code in {402, 422, 503, 504} or exc.status_code >= 500:
            record_event(
                session,
                action=audit_events.AI_CASE_SUMMARY_FAILED,
                resource_type="tenant",
                resource_id=str(tenant.id),
                organisation_id=ctx.organisation_id,
                actor_user_id=ctx.user_id,
                actor_role=ctx.role.value,
                outcome=AuditOutcome.DENIED if exc.status_code == 402 else AuditOutcome.FAILURE,
                summary="Case summary generation failed",
                metadata={"tenant_id": str(tenant.id), "status_code": exc.status_code},
                raise_on_error=False,
            )
        raise

    try:
        result = _accept_result(result, packet)
    except HTTPException:
        record_event(
            session,
            action=audit_events.AI_CASE_SUMMARY_FAILED,
            resource_type="tenant",
            resource_id=str(tenant.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Case summary failed validation",
            metadata={"tenant_id": str(tenant.id)},
            raise_on_error=False,
        )
        raise

    sections = result["sections"]
    row = CaseSummary(
        id=uuid.uuid4(),
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        version_number=_next_version(session, ctx.organisation_id, tenant.id),
        source_fingerprint=fingerprint,
        requested_by_user_id=ctx.user_id,
        request_id=request_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider,
        model_id=model_id,
        generation_method=result.get("generation_method"),
        status="pending_review",
        sections_json=sections,
        missing_information_json=list(result.get("missing_information") or []),
        recorded_concerns_json=list(result.get("recorded_concerns") or []),
        source_refs_json=list(packet.get("sources") or []),
        covered_from=result.get("covered_from"),
        covered_to=result.get("covered_to"),
        uncertainty_notes=result.get("uncertainty_notes"),
        generated_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.AI_CASE_SUMMARY_COMPLETED if not force else audit_events.AI_CASE_SUMMARY_REGENERATED,
        resource_type="case_summary",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Case summary generated — pending human review",
        metadata={"tenant_id": str(tenant.id), "version_number": row.version_number},
        raise_on_error=False,
    )
    # F3.14 — preserve packet sources; no fabricated confidence.
    from app.ai_transparency.service import attach_transparency, record_local_activity

    if request_id:
        if not attach_transparency(
            session,
            request_id=request_id,
            organisation_id=ctx.organisation_id,
            source_refs=row.source_refs_json,
            confidence_kind="unavailable",
            human_approval_status="pending",
            output_ref={"type": "case_summary", "id": str(row.id)},
            operation_type="case_summary",
        ):
            record_local_activity(
                session,
                organisation_id=ctx.organisation_id,
                request_id=request_id,
                feature_id="ai.agent.case_summary",
                workflow_id="case_summary",
                user_id=ctx.user_id,
                execution_status="completed",
                prompt_id=prompt_id,
                prompt_version=prompt_version,
                provider=provider,
                model_id=model_id,
                source_refs=row.source_refs_json,
                confidence_kind="unavailable",
                human_approval_status="pending",
                output_ref={"type": "case_summary", "id": str(row.id)},
                operation_type="case_summary",
            )
    return {**_public(row, current_fingerprint=fingerprint), "idempotent": False, "regenerated": force}


def get_summary(session: Session, ctx: OrganisationContext, summary_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: case_access.require_read(ctx), summary_id=summary_id)
    row = session.get(CaseSummary, summary_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Case summary not found")
    try:
        assert_same_organisation(ctx, row.organisation_id)
    except HTTPException as exc:
        if exc.status_code == 403:
            _audit_denied(ctx, tenant_id=row.tenant_id, summary_id=row.id)
        raise
    tenant = _guard(ctx, lambda: case_access.assert_case_access(session, ctx, row.tenant_id), tenant_id=row.tenant_id, summary_id=row.id)
    packet = collect_case_packet(session, organisation_id=ctx.organisation_id, tenant=tenant)
    return _public(row, current_fingerprint=source_fingerprint(packet))


def list_versions(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, *, page: int, page_size: int) -> dict[str, Any]:
    _guard(ctx, lambda: case_access.require_read(ctx), tenant_id=tenant_id)
    _guard(ctx, lambda: case_access.assert_case_access(session, ctx, tenant_id), tenant_id=tenant_id)
    rows = list(
        session.scalars(
            select(CaseSummary)
            .where(CaseSummary.organisation_id == ctx.organisation_id, CaseSummary.tenant_id == tenant_id)
            .order_by(CaseSummary.version_number.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return {"page": page, "page_size": page_size, "items": [_public(row) for row in rows]}


def regenerate_summary(
    session: Session,
    ctx: OrganisationContext,
    summary_id: uuid.UUID,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    row = session.get(CaseSummary, summary_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Case summary not found")
    try:
        assert_same_organisation(ctx, row.organisation_id)
    except HTTPException as exc:
        if exc.status_code == 403:
            _audit_denied(ctx, summary_id=summary_id)
        raise
    return generate_summary(session, ctx, tenant_id=row.tenant_id, force=True, settings=settings)


def review_summary(
    session: Session,
    ctx: OrganisationContext,
    summary_id: uuid.UUID,
    *,
    decision: str,
    review_comment: str | None,
) -> dict[str, Any]:
    _guard(ctx, lambda: case_access.require_review(ctx), summary_id=summary_id)
    row = session.get(CaseSummary, summary_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Case summary not found")
    try:
        assert_same_organisation(ctx, row.organisation_id)
    except HTTPException as exc:
        if exc.status_code == 403:
            _audit_denied(ctx, summary_id=summary_id)
        raise
    _guard(
        ctx,
        lambda: case_access.assert_case_access(session, ctx, row.tenant_id),
        tenant_id=row.tenant_id,
        summary_id=row.id,
    )
    if row.status != "pending_review":
        raise HTTPException(status_code=409, detail="Case summary is not awaiting review")
    # Approval is a human action. There is no AI actor that can set this status.
    row.status = "approved" if decision == "approve" else "rejected"
    row.reviewed_by_user_id = ctx.user_id
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_comment = review_comment
    session.flush()
    record_event(
        session,
        action=audit_events.AI_CASE_SUMMARY_APPROVED if decision == "approve" else audit_events.AI_CASE_SUMMARY_REJECTED,
        resource_type="case_summary",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Case summary {row.status}",
        metadata={"tenant_id": str(row.tenant_id), "version_number": row.version_number},
        raise_on_error=False,
    )
    return get_summary(session, ctx, summary_id)
