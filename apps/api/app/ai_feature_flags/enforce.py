"""Helpers for background jobs to honour F3.15 flags without a user context."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai_feature_flags.service import evaluate_availability, is_feature_available
from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event

logger = logging.getLogger("hmore.ai_feature_flags.enforce")


def skip_if_disabled(
    session: Session,
    *,
    organisation_id: UUID,
    feature_id: str,
) -> dict[str, Any] | None:
    """Return a skip payload when the feature is unavailable; otherwise None."""
    decision = evaluate_availability(
        session, organisation_id=organisation_id, feature_id=feature_id, use_cache=True
    )
    if decision.available:
        return None
    record_event(
        session,
        action=audit_events.AI_FEATURE_EXECUTION_BLOCKED,
        resource_type="organisation_ai_feature_flag",
        resource_id=decision.feature_id,
        organisation_id=organisation_id,
        actor_user_id=None,
        actor_role=None,
        outcome=AuditOutcome.DENIED,
        summary=f"Background AI feature blocked: {decision.feature_id}",
        metadata={"feature_id": decision.feature_id, "reason": decision.reason, "job": True},
        raise_on_error=False,
    )
    logger.info(
        "ai_feature_job_skipped org=%s feature=%s reason=%s",
        organisation_id,
        decision.feature_id,
        decision.reason,
    )
    return {
        "skipped": True,
        "reason": "ai_feature_disabled",
        "feature_id": decision.feature_id,
        "detail": decision.reason,
    }


def org_feature_enabled(session: Session, organisation_id: UUID, feature_id: str) -> bool:
    return is_feature_available(session, organisation_id=organisation_id, feature_id=feature_id)
