"""F3.14 AI activity logging, transparency reads, and wrong-answer feedback."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.ai_transparency import access as tx_access
from app.ai_transparency.confidence import resolve_confidence
from app.ai_transparency.constants import (
    FEATURE_AGENT_NAMES,
    FEEDBACK_CATEGORIES,
    FEEDBACK_REVIEW_STATUSES,
    INITIATOR_VISIBILITY_FEATURES,
    MAX_FEEDBACK_EXPLANATION,
    MAX_FEEDBACK_PER_HOUR,
)
from app.ai_transparency.sources import sanitize_source_refs, sources_available
from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.auth.tokens import http_403
from app.db.models.ai_activity import AiActivityLog, AiFeedbackReviewEvent, AiWrongAnswerFeedback
from app.db.models.ai_usage import AiUsageRecord
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext

logger = logging.getLogger("hmore.ai_transparency")


def _agent_name(feature_id: str, workflow_id: str) -> str:
    if feature_id in FEATURE_AGENT_NAMES:
        return FEATURE_AGENT_NAMES[feature_id]
    return workflow_id.replace("_", " ").title()[:128]


def _default_visibility(feature_id: str) -> str:
    return "initiator" if feature_id in INITIATOR_VISIBILITY_FEATURES else "staff"


def _extract_transparency(metadata: dict[str, Any] | None) -> dict[str, Any]:
    meta = metadata or {}
    block = meta.get("transparency") if isinstance(meta.get("transparency"), dict) else {}
    return block if isinstance(block, dict) else {}


def ensure_activity_from_usage(
    session: Session,
    record: AiUsageRecord,
    *,
    metadata: dict[str, Any] | None = None,
) -> AiActivityLog | None:
    """Create or return activity log for a usage record. Never stores prompts/outputs."""
    existing = session.scalars(
        select(AiActivityLog).where(AiActivityLog.request_id == record.request_id)
    ).first()
    if existing:
        return existing

    try:
        tx = _extract_transparency(metadata)
        refs = sanitize_source_refs(tx.get("source_refs"))
        kind, label, detail = resolve_confidence(
            kind=tx.get("confidence_kind"),
            detail=tx.get("confidence_detail") if isinstance(tx.get("confidence_detail"), dict) else None,
            label_override=tx.get("confidence_label") if isinstance(tx.get("confidence_label"), str) else None,
        )
        visibility = tx.get("visibility") if tx.get("visibility") in {"staff", "initiator"} else None
        if visibility is None:
            visibility = _default_visibility(record.feature_id)

        error_category = None
        if record.execution_status == "failed":
            error_category = str(tx.get("error_category") or "execution_failed")[:64]
        elif record.execution_status == "rejected_budget":
            error_category = "budget_cap"

        human_approval = str(tx.get("human_approval_status") or "not_applicable")
        if human_approval not in {"not_applicable", "pending", "approved", "rejected", "unknown"}:
            human_approval = "not_applicable"

        output_ref = tx.get("output_ref") if isinstance(tx.get("output_ref"), dict) else None
        if output_ref:
            output_ref = {
                k: str(v)[:128]
                for k, v in output_ref.items()
                if k in {"type", "id"} and v is not None
            } or None

        routing: dict[str, Any] = {}
        if record.escalation_occurred is not None:
            routing["escalation_occurred"] = bool(record.escalation_occurred)
        if record.escalation_reason:
            routing["escalation_reason"] = str(record.escalation_reason)[:128]
        if record.cache_hit is not None:
            routing["cache_hit"] = bool(record.cache_hit)

        activity = AiActivityLog(
            id=uuid.uuid4(),
            organisation_id=record.organisation_id,
            request_id=record.request_id,
            usage_record_id=record.id,
            initiating_user_id=record.user_id,
            feature_id=record.feature_id,
            workflow_id=record.workflow_id,
            agent_name=_agent_name(record.feature_id, record.workflow_id),
            operation_type=str(tx.get("operation_type") or "ai_operation")[:64],
            started_at=None,
            completed_at=record.executed_at,
            execution_status=record.execution_status,
            prompt_id=record.prompt_id,
            prompt_version=record.prompt_version,
            provider=record.provider,
            model_id=record.model_id,
            routing_info_json=routing,
            duration_ms=record.duration_ms,
            cost_status=record.cost_status,
            source_refs_json=refs,
            sources_available=sources_available(refs),
            output_ref_json=output_ref,
            human_approval_status=human_approval,
            error_category=error_category,
            confidence_kind=kind,
            confidence_label=label,
            confidence_detail_json=detail,
            visibility=visibility,
            metadata_safe_json={
                k: str(v)[:128]
                for k, v in (tx.get("safe_tags") or {}).items()
                if isinstance(tx.get("safe_tags"), dict) and isinstance(v, (str, int, bool))
            },
        )
        session.add(activity)
        session.flush()

        action = audit_events.AI_ACTIVITY_COMPLETED
        if record.execution_status == "failed":
            action = audit_events.AI_ACTIVITY_FAILED
        elif record.execution_status in {"started"}:
            action = audit_events.AI_ACTIVITY_CREATED
        record_event(
            session,
            action=action,
            resource_type="ai_activity_log",
            resource_id=str(activity.id),
            organisation_id=record.organisation_id,
            actor_user_id=record.user_id,
            actor_role=None,
            outcome=AuditOutcome.SUCCESS
            if record.execution_status == "completed"
            else AuditOutcome.FAILURE,
            summary=f"AI activity {record.execution_status}: {activity.agent_name}",
            metadata={
                "request_id": record.request_id,
                "feature_id": record.feature_id,
                "execution_status": record.execution_status,
                "sources_available": activity.sources_available,
                "confidence_kind": activity.confidence_kind,
            },
            raise_on_error=False,
        )
        return activity
    except Exception:  # noqa: BLE001
        # Logging must not break AI operations; audit elsewhere still records usage.
        logger.exception("ai_activity_log_create_failed request_id=%s", record.request_id)
        return None


def record_local_activity(
    session: Session,
    *,
    organisation_id: UUID,
    request_id: str,
    feature_id: str,
    workflow_id: str,
    user_id: UUID | None,
    execution_status: str,
    prompt_id: str | None = None,
    prompt_version: str | None = None,
    provider: str | None = None,
    model_id: str | None = None,
    source_refs: Any = None,
    confidence_kind: str | None = None,
    confidence_detail: dict[str, Any] | None = None,
    human_approval_status: str = "pending",
    output_ref: dict[str, Any] | None = None,
    operation_type: str = "ai_operation",
    visibility: str | None = None,
    duration_ms: int | None = None,
    error_category: str | None = None,
) -> AiActivityLog | None:
    """Record activity when a workflow completes outside (or before) usage metering."""
    existing = session.scalars(
        select(AiActivityLog).where(AiActivityLog.request_id == request_id)
    ).first()
    if existing:
        return attach_transparency(
            session,
            request_id=request_id,
            organisation_id=organisation_id,
            source_refs=source_refs,
            confidence_kind=confidence_kind,
            confidence_detail=confidence_detail,
            human_approval_status=human_approval_status,
            output_ref=output_ref,
            operation_type=operation_type,
            visibility=visibility,
        )

    refs = sanitize_source_refs(source_refs)
    kind, label, detail = resolve_confidence(kind=confidence_kind, detail=confidence_detail)
    try:
        activity = AiActivityLog(
            id=uuid.uuid4(),
            organisation_id=organisation_id,
            request_id=request_id,
            usage_record_id=None,
            initiating_user_id=user_id,
            feature_id=feature_id,
            workflow_id=workflow_id,
            agent_name=_agent_name(feature_id, workflow_id),
            operation_type=operation_type[:64],
            completed_at=datetime.now(timezone.utc),
            execution_status=execution_status
            if execution_status in {"completed", "failed", "rejected_budget", "cancelled", "started"}
            else "completed",
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            provider=provider,
            model_id=model_id,
            routing_info_json={},
            duration_ms=duration_ms,
            cost_status="unavailable",
            source_refs_json=refs,
            sources_available=sources_available(refs),
            output_ref_json={
                k: str(v)[:128] for k, v in (output_ref or {}).items() if k in {"type", "id"}
            }
            or None,
            human_approval_status=human_approval_status
            if human_approval_status
            in {"not_applicable", "pending", "approved", "rejected", "unknown"}
            else "not_applicable",
            error_category=error_category,
            confidence_kind=kind,
            confidence_label=label,
            confidence_detail_json=detail,
            visibility=visibility
            if visibility in {"staff", "initiator"}
            else _default_visibility(feature_id),
            metadata_safe_json={},
        )
        session.add(activity)
        session.flush()
        record_event(
            session,
            action=audit_events.AI_ACTIVITY_COMPLETED
            if activity.execution_status == "completed"
            else audit_events.AI_ACTIVITY_FAILED,
            resource_type="ai_activity_log",
            resource_id=str(activity.id),
            organisation_id=organisation_id,
            actor_user_id=user_id,
            actor_role=None,
            outcome=AuditOutcome.SUCCESS
            if activity.execution_status == "completed"
            else AuditOutcome.FAILURE,
            summary=f"AI activity recorded: {activity.agent_name}",
            metadata={
                "request_id": request_id,
                "feature_id": feature_id,
                "sources_available": activity.sources_available,
                "confidence_kind": kind,
            },
            raise_on_error=False,
        )
        return activity
    except Exception:  # noqa: BLE001
        logger.exception("ai_activity_local_record_failed request_id=%s", request_id)
        return None


def attach_transparency(
    session: Session,
    *,
    request_id: str,
    organisation_id: UUID,
    source_refs: Any = None,
    confidence_kind: str | None = None,
    confidence_detail: dict[str, Any] | None = None,
    confidence_label: str | None = None,
    human_approval_status: str | None = None,
    output_ref: dict[str, Any] | None = None,
    operation_type: str | None = None,
    visibility: str | None = None,
) -> AiActivityLog | None:
    """Enrich an existing activity with genuine sources/confidence from the workflow."""
    activity = session.scalars(
        select(AiActivityLog).where(
            AiActivityLog.request_id == request_id,
            AiActivityLog.organisation_id == organisation_id,
        )
    ).first()
    if activity is None:
        return None

    if source_refs is not None:
        refs = sanitize_source_refs(source_refs)
        activity.source_refs_json = refs
        activity.sources_available = sources_available(refs)

    if confidence_kind is not None or confidence_detail is not None or confidence_label is not None:
        kind, label, detail = resolve_confidence(
            kind=confidence_kind or activity.confidence_kind,
            detail=confidence_detail,
            label_override=confidence_label,
        )
        activity.confidence_kind = kind
        activity.confidence_label = label
        activity.confidence_detail_json = detail

    if human_approval_status in {"not_applicable", "pending", "approved", "rejected", "unknown"}:
        activity.human_approval_status = human_approval_status  # type: ignore[assignment]

    if output_ref and isinstance(output_ref, dict):
        activity.output_ref_json = {
            k: str(v)[:128] for k, v in output_ref.items() if k in {"type", "id"} and v is not None
        } or None

    if operation_type:
        activity.operation_type = operation_type[:64]
    if visibility in {"staff", "initiator"}:
        activity.visibility = visibility

    session.flush()
    return activity


def _activity_visible(ctx: OrganisationContext, row: AiActivityLog) -> bool:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return True
    if row.organisation_id != ctx.organisation_id:
        return False
    if tx_access.is_tenant_role(ctx):
        # Tenants only see their own initiator-scoped activities.
        return (
            row.visibility == "initiator"
            and row.initiating_user_id is not None
            and row.initiating_user_id == ctx.user.id
        )
    if row.visibility == "initiator":
        # Staff may see initiator activities only if they initiated them or can review feedback.
        if row.initiating_user_id == ctx.user.id:
            return True
        return ctx.authorization.has_permission(Permission.AI_ACTIVITY_FEEDBACK_REVIEW)
    return tx_access.can_view_staff_activity(ctx)


def _public_activity(
    row: AiActivityLog,
    *,
    include_cost: bool = False,
    usage: AiUsageRecord | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "request_id": row.request_id,
        "initiating_user_id": str(row.initiating_user_id) if row.initiating_user_id else None,
        "feature_id": row.feature_id,
        "workflow_id": row.workflow_id,
        "agent_name": row.agent_name,
        "operation_type": row.operation_type,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "execution_status": row.execution_status,
        "prompt_id": row.prompt_id,
        "prompt_version": row.prompt_version,
        "provider": row.provider,
        "model_id": row.model_id,
        "routing_info": row.routing_info_json or {},
        "duration_ms": row.duration_ms,
        "sources_available": row.sources_available,
        "source_refs": list(row.source_refs_json or []) if row.sources_available else [],
        "source_notice": None
        if row.sources_available
        else "No available source references for this AI result.",
        "output_ref": row.output_ref_json,
        "human_approval_status": row.human_approval_status,
        "error_category": row.error_category,
        "confidence": {
            "kind": row.confidence_kind,
            "label": row.confidence_label,
            "detail": row.confidence_detail_json or {},
            "calibrated": False,
            "percentage": None,
        },
        "visibility": row.visibility,
    }
    if include_cost:
        payload["cost_status"] = row.cost_status
        if usage is not None:
            payload["usage"] = {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
                "cost_amount": str(usage.cost_amount) if usage.cost_amount is not None else None,
                "currency": usage.currency,
                "cost_status": usage.cost_status,
            }
    return payload


def list_activities(
    session: Session,
    ctx: OrganisationContext,
    *,
    limit: int = 20,
    offset: int = 0,
    feature_id: str | None = None,
    execution_status: str | None = None,
    sources_only: bool | None = None,
) -> dict[str, Any]:
    tx_access.require_activity_read(ctx)
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    clauses = [AiActivityLog.organisation_id == ctx.organisation_id]
    if feature_id:
        clauses.append(AiActivityLog.feature_id == feature_id)
    if execution_status:
        clauses.append(AiActivityLog.execution_status == execution_status)
    if sources_only is True:
        clauses.append(AiActivityLog.sources_available.is_(True))
    elif sources_only is False:
        clauses.append(AiActivityLog.sources_available.is_(False))

    if tx_access.is_tenant_role(ctx):
        clauses.append(AiActivityLog.visibility == "initiator")
        clauses.append(AiActivityLog.initiating_user_id == ctx.user.id)
    else:
        # Staff: staff-visible + own initiator activities (+ reviewers see all initiator)
        if (
            ctx.authorization.has_permission(Permission.AI_ACTIVITY_FEEDBACK_REVIEW)
            or ctx.role == HMoreRole.SUPER_ADMIN
        ):
            pass  # org-scoped only
        else:
            clauses.append(
                or_(
                    AiActivityLog.visibility == "staff",
                    and_(
                        AiActivityLog.visibility == "initiator",
                        AiActivityLog.initiating_user_id == ctx.user.id,
                    ),
                )
            )

    total = session.scalar(select(func.count()).select_from(AiActivityLog).where(*clauses)) or 0
    rows = list(
        session.scalars(
            select(AiActivityLog)
            .where(*clauses)
            .order_by(AiActivityLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    include_cost = (
        ctx.authorization.has_permission(Permission.AI_USAGE_READ) or ctx.role == HMoreRole.SUPER_ADMIN
    )

    items = []
    for row in rows:
        if not _activity_visible(ctx, row):
            continue
        usage = session.get(AiUsageRecord, row.usage_record_id) if row.usage_record_id and include_cost else None
        items.append(_public_activity(row, include_cost=include_cost, usage=usage))

    return {"items": items, "total": int(total), "limit": limit, "offset": offset}


def get_activity(
    session: Session,
    ctx: OrganisationContext,
    activity_id: UUID,
    *,
    audit_source_access: bool = False,
) -> dict[str, Any]:
    tx_access.require_activity_read(ctx)
    row = session.get(AiActivityLog, activity_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI activity not found")
    if not _activity_visible(ctx, row):
        raise http_403("Not authorised to view this AI activity")

    include_cost = (
        ctx.authorization.has_permission(Permission.AI_USAGE_READ) or ctx.role == HMoreRole.SUPER_ADMIN
    )
    usage = session.get(AiUsageRecord, row.usage_record_id) if row.usage_record_id and include_cost else None
    payload = _public_activity(row, include_cost=include_cost, usage=usage)

    if audit_source_access and row.sources_available:
        record_event(
            session,
            action=audit_events.AI_ACTIVITY_SOURCES_ACCESSED,
            resource_type="ai_activity_log",
            resource_id=str(row.id),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user.id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.SUCCESS,
            summary="AI activity source references viewed",
            metadata={"source_count": len(row.source_refs_json or [])},
            raise_on_error=False,
        )
    return payload


def _rate_limit_feedback(session: Session, *, organisation_id: UUID, user_id: UUID) -> None:
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = session.scalar(
        select(func.count())
        .select_from(AiWrongAnswerFeedback)
        .where(
            AiWrongAnswerFeedback.organisation_id == organisation_id,
            AiWrongAnswerFeedback.reporting_user_id == user_id,
            AiWrongAnswerFeedback.created_at >= since,
        )
    ) or 0
    if int(count) >= MAX_FEEDBACK_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Feedback rate limit exceeded. Try again later.",
        )


def submit_feedback(
    session: Session,
    ctx: OrganisationContext,
    *,
    activity_id: UUID,
    category: str,
    explanation: str | None = None,
) -> dict[str, Any]:
    tx_access.require_feedback_submit(ctx)
    if category not in FEEDBACK_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid feedback category. Allowed: {sorted(FEEDBACK_CATEGORIES)}",
        )

    activity = session.get(AiActivityLog, activity_id)
    if activity is None or activity.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI activity not found")
    if not _activity_visible(ctx, activity):
        raise http_403("Not authorised to submit feedback for this AI activity")

    _rate_limit_feedback(session, organisation_id=ctx.organisation_id, user_id=ctx.user.id)

    clean_explanation = None
    if explanation is not None:
        clean_explanation = explanation.strip()[:MAX_FEEDBACK_EXPLANATION] or None
        # Treat feedback as untrusted text — never execute; strip nulls.
        if clean_explanation:
            clean_explanation = clean_explanation.replace("\x00", "")

    feedback = AiWrongAnswerFeedback(
        id=uuid.uuid4(),
        organisation_id=ctx.organisation_id,
        activity_id=activity.id,
        reporting_user_id=ctx.user.id,
        category=category,
        explanation=clean_explanation,
        review_status="submitted",
    )
    session.add(feedback)
    session.flush()

    session.add(
        AiFeedbackReviewEvent(
            id=uuid.uuid4(),
            organisation_id=ctx.organisation_id,
            feedback_id=feedback.id,
            actor_user_id=ctx.user.id,
            from_status=None,
            to_status="submitted",
            notes="Feedback submitted",
        )
    )
    session.flush()

    record_event(
        session,
        action=audit_events.AI_FEEDBACK_SUBMITTED,
        resource_type="ai_wrong_answer_feedback",
        resource_id=str(feedback.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user.id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Wrong-answer feedback submitted",
        metadata={
            "activity_id": str(activity.id),
            "category": category,
            "feature_id": activity.feature_id,
        },
        raise_on_error=False,
    )
    return _public_feedback(feedback)


def _public_feedback(row: AiWrongAnswerFeedback, *, events: list[AiFeedbackReviewEvent] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "activity_id": str(row.activity_id),
        "reporting_user_id": str(row.reporting_user_id),
        "category": row.category,
        "explanation": row.explanation,
        "review_status": row.review_status,
        "assigned_reviewer_id": str(row.assigned_reviewer_id) if row.assigned_reviewer_id else None,
        "resolution_notes": row.resolution_notes,
        "rejection_reason": row.rejection_reason,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "resolved_by_user_id": str(row.resolved_by_user_id) if row.resolved_by_user_id else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if events is not None:
        payload["review_history"] = [
            {
                "id": str(e.id),
                "from_status": e.from_status,
                "to_status": e.to_status,
                "notes": e.notes,
                "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
                "event_at": e.event_at.isoformat() if e.event_at else None,
            }
            for e in events
        ]
    return payload


def list_feedback(
    session: Session,
    ctx: OrganisationContext,
    *,
    limit: int = 20,
    offset: int = 0,
    review_status: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    tx_access.require_feedback_review(ctx)
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    clauses = [AiWrongAnswerFeedback.organisation_id == ctx.organisation_id]
    if review_status:
        if review_status not in FEEDBACK_REVIEW_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid review_status filter")
        clauses.append(AiWrongAnswerFeedback.review_status == review_status)
    if category:
        if category not in FEEDBACK_CATEGORIES:
            raise HTTPException(status_code=422, detail="Invalid category filter")
        clauses.append(AiWrongAnswerFeedback.category == category)

    total = session.scalar(select(func.count()).select_from(AiWrongAnswerFeedback).where(*clauses)) or 0
    rows = list(
        session.scalars(
            select(AiWrongAnswerFeedback)
            .where(*clauses)
            .order_by(AiWrongAnswerFeedback.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return {
        "items": [_public_feedback(r) for r in rows],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


def get_feedback(
    session: Session,
    ctx: OrganisationContext,
    feedback_id: UUID,
) -> dict[str, Any]:
    tx_access.require_feedback_review(ctx)
    row = session.get(AiWrongAnswerFeedback, feedback_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Feedback not found")
    events = list(
        session.scalars(
            select(AiFeedbackReviewEvent)
            .where(AiFeedbackReviewEvent.feedback_id == row.id)
            .order_by(AiFeedbackReviewEvent.event_at.asc())
        )
    )
    return _public_feedback(row, events=events)


def review_feedback(
    session: Session,
    ctx: OrganisationContext,
    feedback_id: UUID,
    *,
    action: str,
    resolution_notes: str | None = None,
    rejection_reason: str | None = None,
    assigned_reviewer_id: UUID | None = None,
) -> dict[str, Any]:
    """Human review only — never auto-trains models or changes operational records."""
    tx_access.require_feedback_review(ctx)
    row = session.get(AiWrongAnswerFeedback, feedback_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Feedback not found")

    from_status = row.review_status
    now = datetime.now(timezone.utc)
    notes = (resolution_notes or "").strip()[:MAX_FEEDBACK_EXPLANATION] or None
    if notes:
        notes = notes.replace("\x00", "")

    if action == "start_review":
        row.review_status = "under_review"
        if assigned_reviewer_id:
            row.assigned_reviewer_id = assigned_reviewer_id
        else:
            row.assigned_reviewer_id = ctx.user.id
        audit_action = audit_events.AI_FEEDBACK_REVIEWED
    elif action == "assign":
        if assigned_reviewer_id is None:
            raise HTTPException(status_code=422, detail="assigned_reviewer_id required")
        row.assigned_reviewer_id = assigned_reviewer_id
        if row.review_status == "submitted":
            row.review_status = "under_review"
        audit_action = audit_events.AI_FEEDBACK_ASSIGNED
    elif action == "resolve":
        row.review_status = "resolved"
        row.resolution_notes = notes
        row.resolved_at = now
        row.resolved_by_user_id = ctx.user.id
        audit_action = audit_events.AI_FEEDBACK_RESOLVED
    elif action == "reject":
        reason = (rejection_reason or notes or "").strip()[:MAX_FEEDBACK_EXPLANATION]
        if not reason:
            raise HTTPException(status_code=422, detail="rejection_reason required")
        row.review_status = "rejected"
        row.rejection_reason = reason.replace("\x00", "")
        row.resolution_notes = notes
        row.resolved_at = now
        row.resolved_by_user_id = ctx.user.id
        audit_action = audit_events.AI_FEEDBACK_REJECTED
    else:
        raise HTTPException(
            status_code=422,
            detail="action must be start_review, assign, resolve, or reject",
        )

    session.add(
        AiFeedbackReviewEvent(
            id=uuid.uuid4(),
            organisation_id=ctx.organisation_id,
            feedback_id=row.id,
            actor_user_id=ctx.user.id,
            from_status=from_status,
            to_status=row.review_status,
            notes=notes or rejection_reason,
        )
    )
    session.flush()

    record_event(
        session,
        action=audit_action,
        resource_type="ai_wrong_answer_feedback",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user.id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Feedback {action}",
        metadata={
            "from_status": from_status,
            "to_status": row.review_status,
            "activity_id": str(row.activity_id),
            "auto_applied_to_models": False,
            "auto_changed_records": False,
        },
        raise_on_error=False,
    )
    return get_feedback(session, ctx, row.id)


def feedback_stats(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    tx_access.require_feedback_review(ctx)
    rows = session.execute(
        select(AiWrongAnswerFeedback.category, AiWrongAnswerFeedback.review_status, func.count())
        .where(AiWrongAnswerFeedback.organisation_id == ctx.organisation_id)
        .group_by(AiWrongAnswerFeedback.category, AiWrongAnswerFeedback.review_status)
    ).all()
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for category, review_status, count in rows:
        by_category[category] = by_category.get(category, 0) + int(count)
        by_status[review_status] = by_status.get(review_status, 0) + int(count)
    return {
        "by_category": by_category,
        "by_status": by_status,
        "note": "Feedback is a human investigation signal only — not an automatic correction.",
    }
