"""F3.11 duplicate detection service. Search/deterministic only — never mutates source records."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event, record_event_independent
from app.db.models.duplicate_detection import DuplicateDetectionFinding, DuplicateDetectionRun
from app.db.models.file_metadata import FileMetadata
from app.db.models.housing import HousingApplication
from app.db.models.tenant import Tenant
from app.duplicate_detection import access as dd_access
from app.duplicate_detection.matching import SUPPORTED_RECORD_TYPES, record_summary, run_detectors
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation

NOTICE = (
    "Potential Duplicates — Human Review Required. "
    "Similarity indicates matching strength only and does not prove identity. "
    "This feature never deletes or merges records automatically."
)


def _denied(ctx: OrganisationContext) -> None:
    record_event_independent(
        action=audit_events.DUPLICATE_DETECTION_DENIED,
        resource_type="duplicate_detection",
        resource_id="",
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.DENIED,
        summary="Duplicate detection access denied",
        metadata={},
    )


def _guard(ctx: OrganisationContext, fn):
    try:
        return fn()
    except HTTPException as exc:
        if exc.status_code == 403:
            _denied(ctx)
        raise


def _finding_public(row: DuplicateDetectionFinding, *, include_records: bool = False, session: Session | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "run_id": str(row.run_id),
        "record_type": row.record_type,
        "source_record_id": str(row.source_record_id),
        "candidate_record_id": str(row.candidate_record_id),
        "match_strength": row.match_strength,
        "similarity_score": row.similarity_score,
        "matching_fields": row.matching_fields_json or [],
        "matching_reasons": row.matching_reasons_json or [],
        "detected_at": row.detected_at.isoformat() if row.detected_at else None,
        "review_status": row.review_status,
        "reviewed_by_user_id": str(row.reviewed_by_user_id) if row.reviewed_by_user_id else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "review_comment": row.review_comment,
        "identity_proven": False,
        "auto_merged": False,
        "auto_deleted": False,
    }
    if include_records and session is not None:
        payload["source_record"] = record_summary(session, row.record_type, row.source_record_id)
        payload["candidate_record"] = record_summary(session, row.record_type, row.candidate_record_id)
    return payload


def _run_public(row: DuplicateDetectionRun, findings: list[DuplicateDetectionFinding] | None = None) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "trigger": row.trigger,
        "scope_record_types": row.scope_record_types_json or [],
        "source_record_type": row.source_record_type,
        "source_record_id": str(row.source_record_id) if row.source_record_id else None,
        "status": row.status,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "records_scanned": row.records_scanned,
        "candidates_compared": row.candidates_compared,
        "findings_created": row.findings_created,
        "findings_deduplicated": row.findings_deduplicated,
        "error_summary": row.error_summary,
        "used_ai": row.used_ai,
        "notice": NOTICE,
        "findings": [_finding_public(item) for item in (findings or [])],
    }


def _snapshot_counts(session: Session, organisation_id: uuid.UUID) -> dict[str, int]:
    from sqlalchemy import func

    return {
        "tenants": int(
            session.scalar(
                select(func.count()).select_from(Tenant).where(Tenant.organisation_id == organisation_id)
            )
            or 0
        ),
        "applications": int(
            session.scalar(
                select(func.count())
                .select_from(HousingApplication)
                .where(HousingApplication.organisation_id == organisation_id)
            )
            or 0
        ),
        "files": int(
            session.scalar(
                select(func.count())
                .select_from(FileMetadata)
                .where(FileMetadata.organisation_id == organisation_id)
            )
            or 0
        ),
    }


def _open_finding(session: Session, organisation_id: uuid.UUID, dedupe_key: str) -> DuplicateDetectionFinding | None:
    return session.scalar(
        select(DuplicateDetectionFinding).where(
            DuplicateDetectionFinding.organisation_id == organisation_id,
            DuplicateDetectionFinding.dedupe_key == dedupe_key,
            DuplicateDetectionFinding.review_status.in_(
                ("pending", "deferred", "confirmed_duplicate")
            ),
        )
    )


def run_detection(
    session: Session,
    ctx: OrganisationContext,
    *,
    record_types: list[str] | None = None,
    source_record_type: str | None = None,
    source_record_id: uuid.UUID | None = None,
    trigger: str = "manual",
) -> dict[str, Any]:
    _guard(ctx, lambda: dd_access.require_run(ctx))
    from app.ai_feature_flags.service import require_feature_available
    from app.ai_usage.features import FEATURE_DUPLICATE_DETECTION

    require_feature_available(session, ctx, FEATURE_DUPLICATE_DETECTION)
    types = record_types or list(SUPPORTED_RECORD_TYPES)
    for item in types:
        if item not in SUPPORTED_RECORD_TYPES:
            raise HTTPException(status_code=422, detail=f"Unsupported record type: {item}")
    if source_record_type and source_record_type not in SUPPORTED_RECORD_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported source record type")
    if source_record_id and not source_record_type:
        raise HTTPException(status_code=422, detail="source_record_type is required with source_record_id")

    before = _snapshot_counts(session, ctx.organisation_id)
    run = DuplicateDetectionRun(
        organisation_id=ctx.organisation_id,
        trigger=trigger if trigger in {"manual", "scheduled", "record"} else "manual",
        scope_record_types_json=types if not source_record_type else [source_record_type],
        source_record_type=source_record_type,
        source_record_id=source_record_id,
        status="running",
        requested_by_user_id=ctx.user_id,
        used_ai=False,
    )
    session.add(run)
    session.flush()
    record_event(
        session,
        action=audit_events.DUPLICATE_DETECTION_REQUESTED,
        resource_type="duplicate_detection_run",
        resource_id=str(run.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Duplicate detection requested",
        metadata={"types": run.scope_record_types_json, "used_ai": False},
        raise_on_error=False,
    )
    record_event(
        session,
        action=audit_events.DUPLICATE_DETECTION_STARTED,
        resource_type="duplicate_detection_run",
        resource_id=str(run.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Duplicate detection started",
        metadata={},
        raise_on_error=False,
    )

    try:
        scanned, compared, hits = run_detectors(
            session,
            ctx.organisation_id,
            record_types=types,
            source_record_type=source_record_type,
            source_record_id=source_record_id,
        )
        created = 0
        deduped = 0
        for hit in hits:
            existing = _open_finding(session, ctx.organisation_id, hit.dedupe_key())
            if existing is not None:
                existing.last_seen_run_id = run.id
                existing.match_strength = hit.match_strength
                existing.similarity_score = hit.similarity_score
                existing.matching_fields_json = hit.matching_fields
                existing.matching_reasons_json = hit.matching_reasons
                deduped += 1
                continue
            # Dismissed pairs stay dismissed (avoid re-presenting false positives).
            dismissed = session.scalar(
                select(DuplicateDetectionFinding).where(
                    DuplicateDetectionFinding.organisation_id == ctx.organisation_id,
                    DuplicateDetectionFinding.dedupe_key == hit.dedupe_key(),
                    DuplicateDetectionFinding.review_status == "not_duplicate",
                )
            )
            if dismissed is not None:
                deduped += 1
                continue
            left, right = hit.ordered_ids()
            finding = DuplicateDetectionFinding(
                organisation_id=ctx.organisation_id,
                run_id=run.id,
                first_run_id=run.id,
                last_seen_run_id=run.id,
                record_type=hit.record_type,
                source_record_id=left,
                candidate_record_id=right,
                dedupe_key=hit.dedupe_key(),
                match_strength=hit.match_strength,
                similarity_score=hit.similarity_score,
                matching_fields_json=hit.matching_fields,
                matching_reasons_json=hit.matching_reasons,
                review_status="pending",
            )
            session.add(finding)
            created += 1
        session.flush()
        run.records_scanned = scanned
        run.candidates_compared = compared
        run.findings_created = created
        run.findings_deduplicated = deduped
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.used_ai = False
        after = _snapshot_counts(session, ctx.organisation_id)
        if after != before:
            raise HTTPException(status_code=500, detail="Duplicate detection must not modify source records")
        record_event(
            session,
            action=audit_events.DUPLICATE_DETECTION_COMPLETED,
            resource_type="duplicate_detection_run",
            resource_id=str(run.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.SUCCESS,
            summary="Duplicate detection completed",
            metadata={"created": created, "deduplicated": deduped, "used_ai": False},
            raise_on_error=False,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.error_summary = type(exc).__name__
        run.completed_at = datetime.now(timezone.utc)
        record_event(
            session,
            action=audit_events.DUPLICATE_DETECTION_FAILED,
            resource_type="duplicate_detection_run",
            resource_id=str(run.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Duplicate detection failed",
            metadata={"error": type(exc).__name__},
            raise_on_error=False,
        )
        session.flush()
        raise

    findings = list(
        session.scalars(
            select(DuplicateDetectionFinding).where(DuplicateDetectionFinding.run_id == run.id)
        )
    )
    return _run_public(run, findings)


def list_runs(session: Session, ctx: OrganisationContext, *, limit: int = 20) -> dict[str, Any]:
    _guard(ctx, lambda: dd_access.require_read(ctx))
    rows = list(
        session.scalars(
            select(DuplicateDetectionRun)
            .where(DuplicateDetectionRun.organisation_id == ctx.organisation_id)
            .order_by(DuplicateDetectionRun.started_at.desc())
            .limit(min(max(limit, 1), 100))
        )
    )
    return {"items": [_run_public(row) for row in rows], "notice": NOTICE}


def get_run(session: Session, ctx: OrganisationContext, run_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: dd_access.require_read(ctx))
    row = session.get(DuplicateDetectionRun, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Detection run not found")
    assert_same_organisation(ctx, row.organisation_id)
    findings = list(
        session.scalars(select(DuplicateDetectionFinding).where(DuplicateDetectionFinding.run_id == run_id))
    )
    return _run_public(row, findings)


def list_findings(
    session: Session,
    ctx: OrganisationContext,
    *,
    review_status: str | None = None,
    record_type: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    _guard(ctx, lambda: dd_access.require_read(ctx))
    stmt = select(DuplicateDetectionFinding).where(
        DuplicateDetectionFinding.organisation_id == ctx.organisation_id
    )
    if review_status:
        stmt = stmt.where(DuplicateDetectionFinding.review_status == review_status)
    if record_type:
        stmt = stmt.where(DuplicateDetectionFinding.record_type == record_type)
    rows = list(
        session.scalars(stmt.order_by(DuplicateDetectionFinding.detected_at.desc()).limit(min(max(limit, 1), 200)))
    )
    return {"items": [_finding_public(row) for row in rows], "notice": NOTICE}


def get_finding(session: Session, ctx: OrganisationContext, finding_id: uuid.UUID) -> dict[str, Any]:
    _guard(ctx, lambda: dd_access.require_read(ctx))
    row = session.get(DuplicateDetectionFinding, finding_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    assert_same_organisation(ctx, row.organisation_id)
    return _finding_public(row, include_records=True, session=session)


def review_finding(
    session: Session,
    ctx: OrganisationContext,
    finding_id: uuid.UUID,
    *,
    decision: str,
    review_comment: str | None,
) -> dict[str, Any]:
    _guard(ctx, lambda: dd_access.require_review(ctx))
    row = session.get(DuplicateDetectionFinding, finding_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    assert_same_organisation(ctx, row.organisation_id)
    mapping = {
        "confirm": "confirmed_duplicate",
        "dismiss": "not_duplicate",
        "defer": "deferred",
    }
    if decision not in mapping:
        raise HTTPException(status_code=422, detail="Invalid review decision")
    before = _snapshot_counts(session, ctx.organisation_id)
    row.review_status = mapping[decision]
    row.reviewed_by_user_id = ctx.user_id
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_comment = review_comment
    session.flush()
    after = _snapshot_counts(session, ctx.organisation_id)
    if after != before:
        raise HTTPException(status_code=500, detail="Review must not modify source records")
    action = {
        "confirm": audit_events.DUPLICATE_DETECTION_CONFIRMED,
        "dismiss": audit_events.DUPLICATE_DETECTION_DISMISSED,
        "defer": audit_events.DUPLICATE_DETECTION_REVIEWED,
    }[decision]
    record_event(
        session,
        action=action,
        resource_type="duplicate_detection_finding",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Duplicate detection finding reviewed",
        metadata={"decision": decision, "record_type": row.record_type},
        raise_on_error=False,
    )
    return _finding_public(row, include_records=True, session=session)
