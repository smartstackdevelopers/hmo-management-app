"""F3.9 compliance sweep pipeline: deterministic rules first, AI explains only."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event, record_event_independent
from app.compliance_agent import access as compliance_access
from app.compliance_agent.ai_client import explain_findings
from app.compliance_agent.rules import (
    NOTICE,
    RuleHit,
    evaluate_rules,
    heuristic_explanation,
    list_rules,
    validate_ai_explanation,
)
from app.core.config import Settings, get_settings
from app.db.models.compliance_agent import ComplianceFinding, ComplianceSweep
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation


def _denied(ctx: OrganisationContext, *, sweep_id: uuid.UUID | None = None) -> None:
    record_event_independent(
        action=audit_events.AI_COMPLIANCE_DENIED,
        resource_type="compliance_sweep",
        resource_id=str(sweep_id or ""),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.DENIED,
        summary="Compliance agent access denied",
        metadata={"sweep_id": str(sweep_id) if sweep_id else None},
    )


def _guard(ctx: OrganisationContext, fn, *, sweep_id: uuid.UUID | None = None):
    try:
        return fn()
    except HTTPException as exc:
        if exc.status_code == 403:
            _denied(ctx, sweep_id=sweep_id)
        raise


def _finding_public(row: ComplianceFinding) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "sweep_id": str(row.sweep_id),
        "first_sweep_id": str(row.first_sweep_id),
        "last_seen_sweep_id": str(row.last_seen_sweep_id),
        "rule_id": row.rule_id,
        "rule_version": row.rule_version,
        "rule_name": row.rule_name,
        "rule_source": row.rule_source,
        "module": row.module,
        "source_record_type": row.source_record_type,
        "source_record_id": str(row.source_record_id),
        "result": row.result,
        "severity": row.severity,
        "title": row.title,
        "detail": row.detail,
        "evidence_refs": row.evidence_refs_json or [],
        "due_date": row.due_date.isoformat() if row.due_date else None,
        "detected_at": row.detected_at.isoformat() if row.detected_at else None,
        "review_status": row.review_status,
        "resolution_status": row.resolution_status,
        "needs_human_verification": row.needs_human_verification,
        "reviewed_by_user_id": str(row.reviewed_by_user_id) if row.reviewed_by_user_id else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "review_comment": row.review_comment,
        "corrective_action_ref": row.corrective_action_ref,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "ai_explanation": row.ai_explanation,
        "ai_generated": bool(row.ai_explanation),
    }


def _sweep_public(row: ComplianceSweep, findings: list[ComplianceFinding] | None = None) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "trigger": row.trigger,
        "scope_modules": row.scope_modules_json or [],
        "status": row.status,
        "requested_by_user_id": str(row.requested_by_user_id) if row.requested_by_user_id else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "rules_evaluated": row.rules_evaluated_json or [],
        "records_evaluated": row.records_evaluated,
        "findings_created": row.findings_created,
        "findings_deduplicated": row.findings_deduplicated,
        "error_summary": row.error_summary,
        "ai_status": row.ai_status,
        "ai_error": row.ai_error,
        "ai_explanation": row.ai_explanation,
        "prompt_id": row.prompt_id,
        "prompt_version": row.prompt_version,
        "provider": row.provider,
        "model_id": row.model_id,
        "feature_id": row.feature_id,
        "generation_method": row.generation_method,
        "legal_certification": False,
        "autonomous_decision": False,
        "notice": NOTICE,
        "findings": [_finding_public(item) for item in (findings or [])],
    }


def _load_findings_for_sweep(session: Session, sweep_id: uuid.UUID) -> list[ComplianceFinding]:
    return list(
        session.scalars(
            select(ComplianceFinding).where(
                ComplianceFinding.sweep_id == sweep_id
            ).order_by(ComplianceFinding.detected_at.desc())
        )
    )


def _open_finding(session: Session, organisation_id: uuid.UUID, dedupe_key: str) -> ComplianceFinding | None:
    return session.scalar(
        select(ComplianceFinding).where(
            ComplianceFinding.organisation_id == organisation_id,
            ComplianceFinding.dedupe_key == dedupe_key,
            ComplianceFinding.resolution_status == "open",
            ComplianceFinding.review_status != "dismissed",
        )
    )


def _dedupe_key(hit: RuleHit) -> str:
    return f"{hit.rule.rule_id}:{hit.source_record_id}:{hit.rule.version}"


def _apply_ai(
    session: Session,
    ctx: OrganisationContext,
    sweep: ComplianceSweep,
    hits: list[RuleHit],
    created: list[ComplianceFinding],
    settings: Settings,
) -> None:
    if not hits:
        sweep.ai_status = "not_needed"
        sweep.ai_explanation = heuristic_explanation([])
        sweep.generation_method = "rules_only"
        return

    compact = [
        {
            "rule_id": hit.rule.rule_id,
            "result": hit.result,
            "title": hit.title,
            "module": hit.rule.module,
            "rule_source": hit.rule.source,
        }
        for hit in hits
    ]
    record_event(
        session,
        action=audit_events.AI_COMPLIANCE_AI_REQUESTED,
        resource_type="compliance_sweep",
        resource_id=str(sweep.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Compliance AI explanation requested",
        metadata={"findings": len(compact)},
        raise_on_error=False,
    )
    try:
        response = explain_findings(
            settings,
            organisation_id=ctx.organisation_id,
            user_id=ctx.user_id,
            role=ctx.role.value,
            findings=compact,
        )
        result = response.get("result") if isinstance(response, dict) else None
        explanation_raw = ""
        if isinstance(result, dict):
            explanation_raw = str(result.get("explanation") or "")
            sweep.prompt_id = result.get("prompt_id")
            sweep.prompt_version = result.get("prompt_version")
            sweep.provider = result.get("provider")
            sweep.model_id = result.get("model_id")
        explanation = validate_ai_explanation(explanation_raw)
        sweep.ai_explanation = explanation
        sweep.ai_status = "completed"
        sweep.generation_method = "rules_plus_ai"
        for finding in created:
            finding.ai_explanation = explanation
        record_event(
            session,
            action=audit_events.AI_COMPLIANCE_AI_COMPLETED,
            resource_type="compliance_sweep",
            resource_id=str(sweep.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.SUCCESS,
            summary="Compliance AI explanation completed",
            metadata={},
            raise_on_error=False,
        )
    except HTTPException as exc:
        sweep.ai_explanation = heuristic_explanation(hits)
        if exc.status_code == 402:
            sweep.ai_status = "skipped_budget"
            action = audit_events.AI_COMPLIANCE_AI_SKIPPED
        elif exc.status_code == 503:
            sweep.ai_status = "skipped_unavailable"
            action = audit_events.AI_COMPLIANCE_AI_SKIPPED
        else:
            sweep.ai_status = "failed"
            sweep.ai_error = "AI explanation failed"
            action = audit_events.AI_COMPLIANCE_AI_FAILED
        sweep.generation_method = "rules_heuristic"
        record_event(
            session,
            action=action,
            resource_type="compliance_sweep",
            resource_id=str(sweep.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.SUCCESS if exc.status_code in {402, 503} else AuditOutcome.FAILURE,
            summary="Compliance AI explanation skipped or failed",
            metadata={"status_code": exc.status_code},
            raise_on_error=False,
        )
    except ValueError as exc:
        sweep.ai_status = "failed"
        sweep.ai_error = "Invalid AI explanation"
        sweep.ai_explanation = heuristic_explanation(hits)
        sweep.generation_method = "rules_heuristic"
        record_event(
            session,
            action=audit_events.AI_COMPLIANCE_AI_FAILED,
            resource_type="compliance_sweep",
            resource_id=str(sweep.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Compliance AI explanation rejected",
            metadata={"reason": str(exc)[:120]},
            raise_on_error=False,
        )


def run_sweep(
    session: Session,
    ctx: OrganisationContext,
    *,
    modules: list[str] | None = None,
    trigger: str = "manual",
    settings: Settings | None = None,
) -> dict[str, Any]:
    _guard(ctx, lambda: compliance_access.require_run(ctx))
    settings = settings or get_settings()
    scope = modules or ["training", "safeguarding", "incidents", "support_plans", "documents", "complaints"]
    sweep = ComplianceSweep(
        organisation_id=ctx.organisation_id,
        trigger=trigger if trigger in {"manual", "scheduled"} else "manual",
        scope_modules_json=scope,
        status="running",
        requested_by_user_id=ctx.user_id,
        rules_evaluated_json=[],
        records_evaluated=0,
        findings_created=0,
        findings_deduplicated=0,
        feature_id="ai.agent.compliance",
    )
    session.add(sweep)
    session.flush()
    record_event(
        session,
        action=audit_events.AI_COMPLIANCE_SWEEP_REQUESTED,
        resource_type="compliance_sweep",
        resource_id=str(sweep.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Compliance sweep requested",
        metadata={"trigger": sweep.trigger, "modules": scope},
        raise_on_error=False,
    )
    record_event(
        session,
        action=audit_events.AI_COMPLIANCE_SWEEP_STARTED,
        resource_type="compliance_sweep",
        resource_id=str(sweep.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Compliance sweep started",
        metadata={},
        raise_on_error=False,
    )

    try:
        rules_run, records, hits = evaluate_rules(session, ctx.organisation_id, modules=scope)
        sweep.rules_evaluated_json = [
            {
                "rule_id": rule.rule_id,
                "version": rule.version,
                "name": rule.name,
                "source": rule.source,
                "module": rule.module,
            }
            for rule in rules_run
        ]
        sweep.records_evaluated = records
        created: list[ComplianceFinding] = []
        deduped = 0
        for hit in hits:
            key = _dedupe_key(hit)
            existing = _open_finding(session, ctx.organisation_id, key)
            if existing is not None:
                existing.last_seen_sweep_id = sweep.id
                existing.detail = hit.detail
                existing.evidence_refs_json = hit.evidence_refs
                existing.due_date = hit.due_date
                deduped += 1
                continue
            finding = ComplianceFinding(
                organisation_id=ctx.organisation_id,
                sweep_id=sweep.id,
                first_sweep_id=sweep.id,
                last_seen_sweep_id=sweep.id,
                rule_id=hit.rule.rule_id,
                rule_version=hit.rule.version,
                rule_name=hit.rule.name,
                rule_source=hit.rule.source,
                module=hit.rule.module,
                source_record_type=hit.rule.record_type,
                source_record_id=hit.source_record_id,
                dedupe_key=key,
                result=hit.result,
                severity=hit.severity,
                title=hit.title,
                detail=hit.detail,
                evidence_refs_json=hit.evidence_refs,
                due_date=hit.due_date,
                review_status="pending",
                resolution_status="open",
                needs_human_verification=True,
            )
            session.add(finding)
            created.append(finding)
        session.flush()
        sweep.findings_created = len(created)
        sweep.findings_deduplicated = deduped
        record_event(
            session,
            action=audit_events.AI_COMPLIANCE_FINDINGS_GENERATED,
            resource_type="compliance_sweep",
            resource_id=str(sweep.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.SUCCESS,
            summary="Compliance findings generated",
            metadata={"created": len(created), "deduplicated": deduped, "records": records},
            raise_on_error=False,
        )
        _apply_ai(session, ctx, sweep, hits, created, settings)
        sweep.status = "completed"
        sweep.completed_at = datetime.now(timezone.utc)
        record_event(
            session,
            action=audit_events.AI_COMPLIANCE_SWEEP_COMPLETED,
            resource_type="compliance_sweep",
            resource_id=str(sweep.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.SUCCESS,
            summary="Compliance sweep completed",
            metadata={"ai_status": sweep.ai_status},
            raise_on_error=False,
        )
    except Exception as exc:  # noqa: BLE001 — persist failed sweep state
        sweep.status = "failed"
        sweep.error_summary = type(exc).__name__
        sweep.completed_at = datetime.now(timezone.utc)
        sweep.ai_explanation = heuristic_explanation([])
        record_event(
            session,
            action=audit_events.AI_COMPLIANCE_SWEEP_FAILED,
            resource_type="compliance_sweep",
            resource_id=str(sweep.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Compliance sweep failed",
            metadata={"error": type(exc).__name__},
            raise_on_error=False,
        )
        session.flush()
        raise

    session.flush()
    return _sweep_public(sweep, _load_findings_for_sweep(session, sweep.id))


def list_rules_catalog(ctx: OrganisationContext) -> dict[str, Any]:
    _guard(ctx, lambda: compliance_access.require_read(ctx))
    return {
        "notice": NOTICE,
        "legal_certification": False,
        "items": [
            {
                "rule_id": rule.rule_id,
                "version": rule.version,
                "name": rule.name,
                "description": rule.description,
                "source": rule.source,
                "module": rule.module,
                "record_type": rule.record_type,
                "severity": rule.severity,
                "enabled": True,
            }
            for rule in list_rules()
        ],
    }


def get_sweep(session: Session, ctx: OrganisationContext, sweep_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: compliance_access.require_read(ctx), sweep_id=sweep_id)
    row = session.get(ComplianceSweep, sweep_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Compliance sweep not found")
    assert_same_organisation(ctx, row.organisation_id)
    findings = list(
        session.scalars(
            select(ComplianceFinding).where(
                ComplianceFinding.organisation_id == ctx.organisation_id,
                ComplianceFinding.last_seen_sweep_id == sweep_id,
            )
        )
    )
    if not findings:
        findings = _load_findings_for_sweep(session, sweep_id)
    return _sweep_public(row, findings)


def list_sweeps(session: Session, ctx: OrganisationContext, *, limit: int = 20) -> dict[str, Any]:
    _guard(ctx, lambda: compliance_access.require_read(ctx))
    rows = list(
        session.scalars(
            select(ComplianceSweep)
            .where(ComplianceSweep.organisation_id == ctx.organisation_id)
            .order_by(ComplianceSweep.started_at.desc())
            .limit(min(max(limit, 1), 100))
        )
    )
    return {"items": [_sweep_public(row) for row in rows], "notice": NOTICE}


def list_findings(
    session: Session,
    ctx: OrganisationContext,
    *,
    module: str | None = None,
    review_status: str | None = None,
    resolution_status: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    _guard(ctx, lambda: compliance_access.require_read(ctx))
    stmt = select(ComplianceFinding).where(ComplianceFinding.organisation_id == ctx.organisation_id)
    if module:
        stmt = stmt.where(ComplianceFinding.module == module)
    if review_status:
        stmt = stmt.where(ComplianceFinding.review_status == review_status)
    if resolution_status:
        stmt = stmt.where(ComplianceFinding.resolution_status == resolution_status)
    rows = list(session.scalars(stmt.order_by(ComplianceFinding.detected_at.desc()).limit(min(max(limit, 1), 200))))
    return {"items": [_finding_public(row) for row in rows], "notice": NOTICE}


def get_finding(session: Session, ctx: OrganisationContext, finding_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: compliance_access.require_read(ctx))
    row = session.get(ComplianceFinding, finding_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Compliance finding not found")
    assert_same_organisation(ctx, row.organisation_id)
    return _finding_public(row)


def review_finding(
    session: Session,
    ctx: OrganisationContext,
    finding_id: uuid.UUID,
    *,
    decision: str,
    review_comment: str | None,
    corrective_action_ref: str | None = None,
) -> dict[str, Any]:
    _guard(ctx, lambda: compliance_access.require_review(ctx))
    row = session.get(ComplianceFinding, finding_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Compliance finding not found")
    assert_same_organisation(ctx, row.organisation_id)
    if decision not in {"confirm", "dismiss", "investigate"}:
        raise HTTPException(status_code=422, detail="Invalid review decision")
    mapping = {"confirm": "confirmed", "dismiss": "dismissed", "investigate": "investigate"}
    row.review_status = mapping[decision]
    row.reviewed_by_user_id = ctx.user_id
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_comment = review_comment
    if corrective_action_ref:
        row.corrective_action_ref = corrective_action_ref
    session.flush()
    action = {
        "confirm": audit_events.AI_COMPLIANCE_FINDING_CONFIRMED,
        "dismiss": audit_events.AI_COMPLIANCE_FINDING_DISMISSED,
        "investigate": audit_events.AI_COMPLIANCE_FINDING_REVIEWED,
    }[decision]
    record_event(
        session,
        action=action,
        resource_type="compliance_finding",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Compliance finding reviewed",
        metadata={"decision": decision, "rule_id": row.rule_id},
        raise_on_error=False,
    )
    return _finding_public(row)


def resolve_finding(
    session: Session,
    ctx: OrganisationContext,
    finding_id: uuid.UUID,
    *,
    review_comment: str | None,
    corrective_action_ref: str | None,
) -> dict[str, Any]:
    _guard(ctx, lambda: compliance_access.require_review(ctx))
    row = session.get(ComplianceFinding, finding_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Compliance finding not found")
    assert_same_organisation(ctx, row.organisation_id)
    row.resolution_status = "resolved"
    row.resolved_at = datetime.now(timezone.utc)
    row.reviewed_by_user_id = ctx.user_id
    row.reviewed_at = datetime.now(timezone.utc)
    if review_comment:
        row.review_comment = review_comment
    if corrective_action_ref:
        row.corrective_action_ref = corrective_action_ref
    session.flush()
    record_event(
        session,
        action=audit_events.AI_COMPLIANCE_FINDING_RESOLVED,
        resource_type="compliance_finding",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Compliance finding resolved by human reviewer",
        metadata={"rule_id": row.rule_id, "corrective_action_ref": corrective_action_ref},
        raise_on_error=False,
    )
    return _finding_public(row)
