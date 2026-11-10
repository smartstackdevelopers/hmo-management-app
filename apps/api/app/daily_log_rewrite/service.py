"""Rewrite draft daily-note text. Never creates a DailyLog."""

from __future__ import annotations

import logging
import uuid
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.daily_log_rewrite.ai_client import execute_daily_log_rewrite
from app.support import access
from app.tenancy.context import OrganisationContext

logger = logging.getLogger("hmore.daily_log_rewrite")

MAX_TEXT = 20000


def _commit_failure_marker(session: Session) -> None:
    """Keep a failure/cap marker when the request is about to raise.

    get_session rolls the request transaction back on HTTPException. Commit first
    so the marker remains. Rewrite never inserts a DailyLog, so this commit does
    not save a note.
    """
    try:
        session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("daily_log_rewrite_failure_commit_failed")


def _budget_http(exc: HTTPException) -> HTTPException:
    message = "Organisation AI usage limit has been reached"
    detail = exc.detail
    if isinstance(detail, dict):
        raw = detail.get("message")
        if isinstance(raw, str) and raw.strip():
            message = raw.strip()[:300]
    elif isinstance(detail, str) and detail.strip():
        message = detail.strip()[:300]
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={"error": "ai_budget_exceeded", "message": message},
    )


def _record_activity(
    session: Session,
    ctx: OrganisationContext,
    *,
    request_id: str,
    execution_status: str,
    prompt_id: str | None = None,
    prompt_version: str | None = None,
    provider: str | None = None,
    model_id: str | None = None,
    error_category: str | None = None,
) -> str | None:
    from app.ai_transparency.service import attach_transparency, record_local_activity
    from app.ai_usage.features import FEATURE_DAILY_LOG_REWRITE

    # Confidence stays unavailable: this workflow has no calibrated score and no sources.
    attached = attach_transparency(
        session,
        request_id=request_id,
        organisation_id=ctx.organisation_id,
        confidence_kind="unavailable",
        human_approval_status="pending" if execution_status == "completed" else "not_applicable",
        operation_type="daily_log_rewrite",
        visibility="staff",
    )
    activity = attached or record_local_activity(
        session,
        organisation_id=ctx.organisation_id,
        request_id=request_id,
        feature_id=FEATURE_DAILY_LOG_REWRITE,
        workflow_id="daily_log_rewrite",
        user_id=ctx.user_id,
        execution_status=execution_status,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider,
        model_id=model_id,
        confidence_kind="unavailable",
        human_approval_status="pending" if execution_status == "completed" else "not_applicable",
        operation_type="daily_log_rewrite",
        visibility="staff",
        error_category=error_category,
    )
    if activity is None:
        return None
    return str(activity.id)


def rewrite_daily_log_draft(
    session: Session,
    ctx: OrganisationContext,
    *,
    text: str,
    tenant_id: UUID | None = None,
    settings: Settings | None = None,
    locale: str = "en-GB",
) -> dict[str, Any]:
    """Return rewritten draft text. The caller must confirm before any daily log is saved."""
    access.require_daily_log_write(ctx)
    if tenant_id is not None:
        access.assert_tenant_support_access(session, ctx, tenant_id)

    from app.ai_feature_flags.service import require_feature_available
    from app.ai_usage.features import FEATURE_DAILY_LOG_REWRITE

    require_feature_available(session, ctx, FEATURE_DAILY_LOG_REWRITE)

    cleaned = (text or "").strip()
    if not cleaned or len(cleaned) > MAX_TEXT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="text must be between 1 and 20000 characters",
        )

    settings = settings or get_settings()
    try:
        raw = execute_daily_log_rewrite(
            settings,
            organisation_id=ctx.organisation_id,
            user_id=ctx.user_id,
            role=ctx.role.value,
            text=cleaned,
            locale=locale,
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_402_PAYMENT_REQUIRED:
            request_id = str(uuid.uuid4())
            record_event(
                session,
                action=audit_events.DAILY_LOG_REWRITE_CAP,
                resource_type="daily_log_rewrite",
                resource_id=request_id,
                organisation_id=ctx.organisation_id,
                actor_user_id=ctx.user_id,
                actor_role=ctx.role.value,
                outcome=AuditOutcome.DENIED,
                summary="Daily log rewrite rejected — AI budget exhausted",
                metadata={"text_length": len(cleaned), "tenant_id": str(tenant_id) if tenant_id else None},
                raise_on_error=False,
            )
            _record_activity(
                session,
                ctx,
                request_id=request_id,
                execution_status="rejected_budget",
                error_category="budget_cap",
            )
            _commit_failure_marker(session)
            raise _budget_http(exc) from exc
        record_event(
            session,
            action=audit_events.DAILY_LOG_REWRITE_FAILED,
            resource_type="daily_log_rewrite",
            resource_id="",
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Daily log rewrite failed",
            metadata={"status_code": exc.status_code},
            raise_on_error=False,
        )
        _commit_failure_marker(session)
        raise

    result = raw.get("result") if isinstance(raw, dict) else None
    if not isinstance(result, dict):
        result = {}
    rewritten = str(result.get("rewritten_text") or "").strip()
    if not rewritten:
        record_event(
            session,
            action=audit_events.DAILY_LOG_REWRITE_FAILED,
            resource_type="daily_log_rewrite",
            resource_id=str(raw.get("request_id") or ""),
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Daily log rewrite returned no text",
            metadata={"saved_daily_log": False},
            raise_on_error=False,
        )
        _commit_failure_marker(session)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI rewrite did not return text. The note was not saved.",
        )

    request_id = str(raw.get("request_id") or uuid.uuid4())
    activity_id = _record_activity(
        session,
        ctx,
        request_id=request_id,
        execution_status="completed",
        prompt_id=result.get("prompt_id"),
        prompt_version=result.get("prompt_version"),
        provider=result.get("provider"),
        model_id=result.get("model_id"),
    )
    record_event(
        session,
        action=audit_events.DAILY_LOG_REWRITE_COMPLETED,
        resource_type="daily_log_rewrite",
        resource_id=request_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Daily log rewrite returned for human confirmation",
        metadata={
            "text_length": len(cleaned),
            "tenant_id": str(tenant_id) if tenant_id else None,
            "activity_id": activity_id,
            "saved_daily_log": False,
        },
        raise_on_error=False,
    )
    prompt_version = result.get("prompt_version")
    return {
        "rewritten_text": rewritten,
        "activity_id": activity_id,
        "request_id": request_id,
        "prompt_version": str(prompt_version) if prompt_version else None,
    }
