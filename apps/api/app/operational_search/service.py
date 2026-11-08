"""F3.12 natural-language operational search. Spec is validated before any query."""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import HTTPException

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event, record_event_independent
from app.core.config import Settings, get_settings
from app.operational_search import access as search_access
from app.operational_search.ai_client import interpret_with_ai
from app.operational_search.execute import execute_spec
from app.operational_search.interpret import SearchSpecError, interpret_question, validate_spec
from app.tenancy.context import OrganisationContext
from sqlalchemy.orm import Session

# Interpretation cache only. Never stores result rows. Key includes organisation id.
_INTERPRET_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_LIMIT = 128


def _cache_key(organisation_id: str, question: str) -> str:
    digest = hashlib.sha256(question.strip().lower().encode("utf-8")).hexdigest()
    return f"{organisation_id}:{digest}"


def _remember(key: str, spec: dict[str, Any]) -> None:
    if len(_INTERPRET_CACHE) >= _CACHE_LIMIT:
        _INTERPRET_CACHE.pop(next(iter(_INTERPRET_CACHE)))
    _INTERPRET_CACHE[key] = spec


def clear_interpret_cache() -> None:
    _INTERPRET_CACHE.clear()


def _denied(ctx: OrganisationContext) -> None:
    record_event_independent(
        action=audit_events.OPERATIONAL_SEARCH_DENIED,
        resource_type="operational_search",
        resource_id="",
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.DENIED,
        summary="Operational search denied",
        metadata={},
    )


def search(
    session: Session,
    ctx: OrganisationContext,
    question: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    try:
        search_access.require_search(ctx)
    except HTTPException:
        _denied(ctx)
        raise
    from app.ai_feature_flags.service import require_feature_available
    from app.ai_usage.features import FEATURE_OPERATIONAL_SEARCH

    require_feature_available(session, ctx, FEATURE_OPERATIONAL_SEARCH)

    key = _cache_key(str(ctx.organisation_id), question)
    cached = _INTERPRET_CACHE.get(key)
    source = "cache"
    try:
        if cached is None:
            raw: dict[str, Any]
            if (settings.ai_service_base_url or "").strip() and (settings.ai_service_token or "").strip():
                source = "ai"
                try:
                    raw = interpret_with_ai(
                        settings,
                        organisation_id=ctx.organisation_id,
                        user_id=ctx.user_id,
                        role=ctx.role.value,
                        question=question,
                    )
                except HTTPException as exc:
                    if exc.status_code == 503:
                        source = "deterministic_fallback"
                        raw = interpret_question(question)
                    else:
                        raise
            else:
                source = "deterministic"
                raw = interpret_question(question)
            spec = validate_spec(raw)
            _remember(key, spec)
        else:
            spec = validate_spec(cached)
    except SearchSpecError as exc:
        record_event(
            session,
            action=audit_events.OPERATIONAL_SEARCH_REJECTED,
            resource_type="operational_search",
            resource_id="",
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Operational search specification rejected",
            metadata={"reason": exc.message[:120]},
            raise_on_error=False,
        )
        raise HTTPException(status_code=422, detail=exc.message) from exc
    except HTTPException as exc:
        if exc.status_code == 402:
            record_event(
                session,
                action=audit_events.OPERATIONAL_SEARCH_CAP,
                resource_type="operational_search",
                resource_id="",
                organisation_id=ctx.organisation_id,
                actor_user_id=ctx.user_id,
                actor_role=ctx.role.value,
                outcome=AuditOutcome.DENIED,
                summary="Operational search usage cap reached",
                metadata={},
                raise_on_error=False,
            )
        raise

    record_event(
        session,
        action=audit_events.OPERATIONAL_SEARCH_REQUESTED,
        resource_type="operational_search",
        resource_id="",
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Operational search requested",
        metadata={"source": source, "outcome": spec.get("outcome"), "entity": spec.get("entity")},
        raise_on_error=False,
    )

    if spec["outcome"] != "ready":
        return {
            "outcome": spec["outcome"],
            "message": spec["message"],
            "items": [],
            "count": 0,
            "interpretation_source": source,
            "executed_sql": False,
        }

    try:
        executed = execute_spec(session, ctx, spec)
    except HTTPException:
        _denied(ctx)
        raise
    return {
        "outcome": "results",
        "message": spec.get("explanation") or "Search completed.",
        "question": question[:500],
        "interpretation": {
            "entity": spec["entity"],
            "preset": spec["preset"],
            "sort": spec["sort"],
            "limit": spec["limit"],
            "offset": spec["offset"],
        },
        "interpretation_source": source,
        "executed_sql": False,
        **executed,
    }
