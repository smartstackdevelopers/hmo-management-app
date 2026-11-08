"""F3.6 document check pipeline: extract, rules, then optional AI gap notes."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event, record_event_independent
from app.core.config import Settings, get_settings
from app.db.models.document_checks import (
    DocumentCheck,
    DocumentCheckFinding,
    DocumentCheckObservation,
    DocumentCheckRule,
)
from app.db.models.managed_documents import ManagedDocumentCategory, ManagedDocumentVersion
from app.document_checks import access as check_access
from app.document_checks.ai_client import explain_gaps
from app.document_checks.explain import explain_findings, validate_ai_observations
from app.document_checks.extract import CHECKER_VERSION, extract_document
from app.document_checks.rules import apply_checks, check_status_for
from app.storage.service import download_file
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation

RULE_KINDS = {"require_extracted_text", "require_expiry_date", "expiry_not_past", "require_phrase"}


def _denied(ctx: OrganisationContext, *, document_id: uuid.UUID | None = None) -> None:
    record_event_independent(
        action=audit_events.AI_DOCUMENT_CHECK_DENIED,
        resource_type="managed_document",
        resource_id=str(document_id or ""),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.DENIED,
        summary="Document check access denied",
        metadata={"document_id": str(document_id) if document_id else None},
    )


def _guard(ctx: OrganisationContext, fn, *, document_id: uuid.UUID | None = None):
    try:
        return fn()
    except HTTPException as exc:
        if exc.status_code == 403:
            _denied(ctx, document_id=document_id)
        raise


def _public(check: DocumentCheck, findings: list[DocumentCheckFinding], observations: list[DocumentCheckObservation]) -> dict[str, Any]:
    return {
        "id": str(check.id),
        "organisation_id": str(check.organisation_id),
        "document_id": str(check.document_id),
        "document_version_id": str(check.document_version_id),
        "checker_version": check.checker_version,
        "status": check.status,
        "extraction_status": check.extraction_status,
        "detected_type": check.detected_type,
        "page_count": check.page_count,
        "summary": check.summary,
        "ai_status": check.ai_status,
        "ai_error": check.ai_error,
        "generation_method": check.generation_method,
        "provider": check.provider,
        "model_id": check.model_id,
        "processed_at": check.processed_at.isoformat() if check.processed_at else None,
        "reviewed_at": check.reviewed_at.isoformat() if check.reviewed_at else None,
        "review_comment": check.review_comment,
        "legal_certification": False,
        "findings": [
            {
                "id": str(row.id),
                "code": row.code,
                "source": row.source,
                "outcome": row.outcome,
                "title": row.title,
                "detail": row.detail,
                "page_number": row.page_number,
                "needs_human_verification": row.needs_human_verification,
                "review_status": row.review_status,
                "origin": row.origin,
            }
            for row in findings
        ],
        "observations": [
            {
                "id": str(row.id),
                "title": row.title,
                "body": row.body,
                "source_finding_code": row.source_finding_code,
                "needs_human_verification": row.needs_human_verification,
                "origin": row.origin,
                "ai_generated": row.origin == "llm",
            }
            for row in observations
        ],
    }


def _load_children(session: Session, check_id: uuid.UUID):
    findings = list(
        session.scalars(select(DocumentCheckFinding).where(DocumentCheckFinding.check_id == check_id))
    )
    observations = list(
        session.scalars(select(DocumentCheckObservation).where(DocumentCheckObservation.check_id == check_id))
    )
    return findings, observations


def _needs_explanation(findings: list[dict[str, Any]], extraction_status: str) -> bool:
    if extraction_status != "extracted":
        return True
    return any(item["outcome"] in {"fail", "warning"} for item in findings)


def run_check(
    session: Session,
    ctx: OrganisationContext,
    *,
    document_id: uuid.UUID,
    force: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    _guard(ctx, lambda: check_access.require_run(ctx), document_id=document_id)
    from app.ai_feature_flags.service import require_feature_available
    from app.ai_usage.features import FEATURE_DOCUMENT_CHECK

    require_feature_available(session, ctx, FEATURE_DOCUMENT_CHECK)
    settings = settings or get_settings()
    doc = _guard(ctx, lambda: check_access.load_document(session, ctx, document_id), document_id=document_id)
    if doc.current_version_id is None:
        raise HTTPException(status_code=409, detail="Document has no version")
    version = session.get(ManagedDocumentVersion, doc.current_version_id)
    if version is None or version.document_id != doc.id:
        raise HTTPException(status_code=404, detail="Document version not found")
    _file, data = download_file(session, ctx, version.file_id)
    digest = hashlib.sha256(data).hexdigest()
    if not force:
        existing = session.scalars(
            select(DocumentCheck)
            .where(
                DocumentCheck.organisation_id == ctx.organisation_id,
                DocumentCheck.document_version_id == version.id,
                DocumentCheck.content_sha256 == digest,
                DocumentCheck.checker_version == CHECKER_VERSION,
                DocumentCheck.status != "processing_failed",
            )
            .order_by(DocumentCheck.created_at.desc())
        ).first()
        if existing is not None:
            findings, observations = _load_children(session, existing.id)
            return {**_public(existing, findings, observations), "idempotent": True}

    record_event(
        session,
        action=audit_events.AI_DOCUMENT_CHECK_REQUESTED,
        resource_type="managed_document",
        resource_id=str(doc.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Document check requested",
        metadata={"document_id": str(doc.id), "document_version_id": str(version.id), "force": force},
        raise_on_error=False,
    )
    category = session.get(ManagedDocumentCategory, doc.category_id)
    category_code = category.code if category else ""
    rules = [
        {
            "category_code": row.category_code,
            "rule_kind": row.rule_kind,
            "parameter": row.parameter,
            "enabled": row.enabled,
        }
        for row in session.scalars(
            select(DocumentCheckRule).where(
                DocumentCheckRule.organisation_id == ctx.organisation_id,
                DocumentCheckRule.enabled.is_(True),
            )
        )
    ]
    extraction = extract_document(data, _file.content_type)
    record_event(
        session,
        action=audit_events.AI_DOCUMENT_CHECK_OCR_COMPLETED
        if extraction["extraction_status"] in {"extracted", "partial", "ocr_unavailable", "unsupported"}
        else audit_events.AI_DOCUMENT_CHECK_OCR_FAILED,
        resource_type="managed_document",
        resource_id=str(doc.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS if extraction["extraction_status"] != "failed" else AuditOutcome.FAILURE,
        summary="Document extraction finished",
        metadata={
            "document_version_id": str(version.id),
            "extraction_status": extraction["extraction_status"],
            "detected_type": extraction["detected_type"],
        },
        raise_on_error=False,
    )
    findings = apply_checks(
        extraction=extraction,
        expiry_date=doc.expiry_date,
        category_code=category_code,
        configured_rules=rules,
        today=datetime.now(timezone.utc).date(),
    )
    record_event(
        session,
        action=audit_events.AI_DOCUMENT_CHECK_RULES_COMPLETED,
        resource_type="managed_document",
        resource_id=str(doc.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Document rules completed",
        metadata={"document_version_id": str(version.id), "finding_count": len(findings)},
        raise_on_error=False,
    )
    ai_status = "not_needed"
    ai_error = None
    generation_method = None
    provider = None
    model_id = None
    prompt_id = None
    prompt_version = None
    observations: list[dict[str, Any]] = []
    if _needs_explanation(findings, extraction["extraction_status"]):
        if (settings.ai_service_base_url or "").strip():
            try:
                raw = explain_gaps(
                    settings,
                    organisation_id=ctx.organisation_id,
                    user_id=ctx.user_id,
                    role=ctx.role.value,
                    findings=findings,
                    excerpt=extraction.get("text") or "",
                )
                payload = (raw.get("result") or {}).get("analysis") or {}
                observations = validate_ai_observations(payload, findings)
                ai_status = "completed"
                generation_method = "llm"
                provider = (raw.get("result") or {}).get("provider")
                model_id = (raw.get("result") or {}).get("model_id")
                prompt_id = (raw.get("result") or {}).get("prompt_id")
                prompt_version = (raw.get("result") or {}).get("prompt_version")
                record_event(
                    session,
                    action=audit_events.AI_DOCUMENT_CHECK_AI_COMPLETED,
                    resource_type="managed_document",
                    resource_id=str(doc.id),
                    organisation_id=ctx.organisation_id,
                    actor_user_id=ctx.user_id,
                    actor_role=ctx.role.value,
                    outcome=AuditOutcome.SUCCESS,
                    summary="Document gap analysis completed",
                    metadata={"document_version_id": str(version.id)},
                    raise_on_error=False,
                )
            except HTTPException as exc:
                if exc.status_code == 402:
                    ai_status = "skipped_budget"
                    ai_error = "ai_budget_exceeded"
                elif exc.status_code == 422:
                    ai_status = "failed"
                    ai_error = "invalid_ai_output"
                else:
                    ai_status = "failed"
                    ai_error = "ai_unavailable"
                observations = []
                record_event(
                    session,
                    action=audit_events.AI_DOCUMENT_CHECK_AI_SKIPPED if ai_status.startswith("skipped") else audit_events.AI_DOCUMENT_CHECK_AI_FAILED,
                    resource_type="managed_document",
                    resource_id=str(doc.id),
                    organisation_id=ctx.organisation_id,
                    actor_user_id=ctx.user_id,
                    actor_role=ctx.role.value,
                    outcome=AuditOutcome.DENIED if exc.status_code == 402 else AuditOutcome.FAILURE,
                    summary="Document gap analysis did not complete",
                    metadata={"document_version_id": str(version.id), "ai_status": ai_status},
                    raise_on_error=False,
                )
            except ValueError:
                ai_status = "failed"
                ai_error = "invalid_ai_output"
                observations = []
        else:
            if settings.is_production:
                ai_status = "skipped_unavailable"
                ai_error = "ai_not_configured"
            else:
                observations = explain_findings(findings)
                ai_status = "heuristic"
                generation_method = "structured_heuristic"
                provider = "heuristic"
                model_id = "structured_heuristic_v1"
                prompt_id = "hmore.document_check.v1"
                prompt_version = "1.0.0"

    status = check_status_for(findings, extraction["extraction_status"])
    fails = sum(1 for item in findings if item["outcome"] == "fail")
    warnings = sum(1 for item in findings if item["outcome"] == "warning")
    summary = (
        f"Checker assistance only — not a legal certification. "
        f"Extraction {extraction['extraction_status']}. Failed checks: {fails}. Warnings: {warnings}. "
        f"AI status: {ai_status}."
    )
    check = DocumentCheck(
        id=uuid.uuid4(),
        organisation_id=ctx.organisation_id,
        document_id=doc.id,
        document_version_id=version.id,
        file_id=version.file_id,
        content_sha256=digest,
        checker_version=CHECKER_VERSION,
        status=status,
        extraction_status=extraction["extraction_status"],
        detected_type=extraction["detected_type"],
        page_count=extraction.get("page_count"),
        extracted_text=(extraction.get("text") or "")[:20000] or None,
        summary=summary,
        ai_status=ai_status,
        ai_error=ai_error,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider,
        model_id=model_id,
        generation_method=generation_method,
        requested_by_user_id=ctx.user_id,
        processed_at=datetime.now(timezone.utc),
    )
    session.add(check)
    session.flush()
    finding_rows = []
    for item in findings:
        row = DocumentCheckFinding(
            id=uuid.uuid4(),
            organisation_id=ctx.organisation_id,
            check_id=check.id,
            code=item["code"],
            source=item["source"],
            outcome=item["outcome"],
            title=item["title"][:200],
            detail=item["detail"],
            page_number=item.get("page_number"),
            needs_human_verification=bool(item.get("needs_human_verification")),
            review_status="pending",
            origin=item["source"],
        )
        session.add(row)
        finding_rows.append(row)
    observation_rows = []
    for item in observations:
        row = DocumentCheckObservation(
            id=uuid.uuid4(),
            organisation_id=ctx.organisation_id,
            check_id=check.id,
            title=item["title"][:200],
            body=item["body"],
            source_finding_code=item["source_finding_code"],
            needs_human_verification=bool(item.get("needs_human_verification", True)),
            origin=item.get("origin") or "structured_heuristic",
        )
        session.add(row)
        observation_rows.append(row)
    session.flush()
    return {**_public(check, finding_rows, observation_rows), "idempotent": False, "document_status_unchanged": doc.status}


def get_check(session: Session, ctx: OrganisationContext, check_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: check_access.require_read(ctx))
    check = session.get(DocumentCheck, check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Document check not found")
    try:
        assert_same_organisation(ctx, check.organisation_id)
    except HTTPException as exc:
        if exc.status_code == 403:
            _denied(ctx, document_id=check.document_id)
        raise
    _guard(ctx, lambda: check_access.load_document(session, ctx, check.document_id), document_id=check.document_id)
    findings, observations = _load_children(session, check.id)
    return _public(check, findings, observations)


def get_text(session: Session, ctx: OrganisationContext, check_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: check_access.require_run(ctx))
    body = get_check(session, ctx, check_id)
    check = session.get(DocumentCheck, check_id)
    return {
        "check_id": body["id"],
        "document_version_id": body["document_version_id"],
        "extraction_status": body["extraction_status"],
        "text": check.extracted_text or "",
    }


def list_checks(session: Session, ctx: OrganisationContext, document_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: check_access.require_read(ctx), document_id=document_id)
    _guard(ctx, lambda: check_access.load_document(session, ctx, document_id), document_id=document_id)
    rows = list(
        session.scalars(
            select(DocumentCheck)
            .where(DocumentCheck.organisation_id == ctx.organisation_id, DocumentCheck.document_id == document_id)
            .order_by(DocumentCheck.created_at.desc())
        )
    )
    items = []
    for row in rows:
        findings, observations = _load_children(session, row.id)
        items.append(_public(row, findings, observations))
    return {"items": items}


def decide_finding(
    session: Session,
    ctx: OrganisationContext,
    finding_id: uuid.UUID,
    *,
    decision: str,
    review_comment: str | None,
) -> dict[str, Any]:
    _guard(ctx, lambda: check_access.require_review(ctx))
    row = session.get(DocumentCheckFinding, finding_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    assert_same_organisation(ctx, row.organisation_id)
    check = session.get(DocumentCheck, row.check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Document check not found")
    doc = _guard(ctx, lambda: check_access.load_document(session, ctx, check.document_id), document_id=check.document_id)
    before = doc.status
    row.review_status = "confirmed" if decision == "confirm" else "dismissed"
    row.reviewed_by_user_id = ctx.user_id
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_comment = review_comment
    session.flush()
    record_event(
        session,
        action=audit_events.AI_DOCUMENT_CHECK_FINDING_CONFIRMED
        if decision == "confirm"
        else audit_events.AI_DOCUMENT_CHECK_FINDING_DISMISSED,
        resource_type="document_check_finding",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Document check finding reviewed",
        metadata={"check_id": str(check.id), "code": row.code},
        raise_on_error=False,
    )
    if doc.status != before:
        raise HTTPException(status_code=500, detail="Review must not change the document")
    return get_check(session, ctx, check.id)


def review_check(
    session: Session,
    ctx: OrganisationContext,
    check_id: uuid.UUID,
    *,
    review_comment: str | None,
) -> dict[str, Any]:
    _guard(ctx, lambda: check_access.require_review(ctx))
    check = session.get(DocumentCheck, check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Document check not found")
    assert_same_organisation(ctx, check.organisation_id)
    doc = check_access.load_document(session, ctx, check.document_id)
    before = doc.status
    check.reviewed_by_user_id = ctx.user_id
    check.reviewed_at = datetime.now(timezone.utc)
    check.review_comment = review_comment
    session.flush()
    record_event(
        session,
        action=audit_events.AI_DOCUMENT_CHECK_REVIEWED,
        resource_type="document_check",
        resource_id=str(check.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Document check marked reviewed",
        metadata={"document_id": str(doc.id), "document_version_id": str(check.document_version_id)},
        raise_on_error=False,
    )
    if doc.status != before:
        raise HTTPException(status_code=500, detail="Review must not change the document")
    return get_check(session, ctx, check.id)


def save_rule(
    session: Session,
    ctx: OrganisationContext,
    *,
    category_code: str,
    rule_kind: str,
    parameter: str,
    enabled: bool,
) -> dict[str, Any]:
    _guard(ctx, lambda: check_access.require_rules(ctx))
    if rule_kind not in RULE_KINDS:
        raise HTTPException(status_code=422, detail="Unknown document check rule")
    code = category_code.strip()
    param = parameter.strip()[:200]
    existing = session.scalars(
        select(DocumentCheckRule).where(
            DocumentCheckRule.organisation_id == ctx.organisation_id,
            DocumentCheckRule.category_code == code,
            DocumentCheckRule.rule_kind == rule_kind,
            DocumentCheckRule.parameter == param,
        )
    ).first()
    if existing is None:
        existing = DocumentCheckRule(
            id=uuid.uuid4(),
            organisation_id=ctx.organisation_id,
            category_code=code,
            rule_kind=rule_kind,
            parameter=param,
            enabled=enabled,
        )
        session.add(existing)
    else:
        existing.enabled = enabled
    session.flush()
    return {
        "id": str(existing.id),
        "category_code": existing.category_code,
        "rule_kind": existing.rule_kind,
        "parameter": existing.parameter,
        "enabled": existing.enabled,
    }
