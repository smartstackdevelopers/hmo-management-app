"""Central audit event recorder. Clients must never invent actor identity."""

from __future__ import annotations

import logging
import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.audit.redaction import sanitize_metadata, sanitize_summary
from app.db.models.audit import AuditEvent

logger = logging.getLogger("hmore.audit")

# Re-entrancy guard: recording audit failures must not recurse into audit writes.
_RECORDING = False


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


def record_event(
    session: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | str | None = None,
    organisation_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    actor_role: str | None = None,
    outcome: AuditOutcome | str = AuditOutcome.SUCCESS,
    correlation_id: str | None = None,
    source: str | None = "api",
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
    raise_on_error: bool = True,
) -> AuditEvent | None:
    """Persist one audit event in the current transaction.

    Transaction policy: by default the event shares the caller's transaction so a
    rolled-back business operation does not leave a success audit row. Use
    ``record_event_independent`` when the caller will raise (e.g. HTTP 403) and the
    security event must still be committed.

    Failures to write are logged and optionally re-raised; they never recursively
    call ``record_event``.
    """
    global _RECORDING
    if _RECORDING:
        logger.error("Skipped recursive audit write action=%s", action)
        return None

    outcome_value = (
        outcome.value if isinstance(outcome, AuditOutcome) else str(outcome)
    ).lower()
    if outcome_value not in {item.value for item in AuditOutcome}:
        raise ValueError(f"Invalid audit outcome: {outcome_value}")
    if not action or len(action) > 100:
        raise ValueError("Invalid audit action")
    if not resource_type or len(resource_type) > 100:
        raise ValueError("Invalid resource_type")

    _RECORDING = True
    try:
        # Nested savepoint so an RLS/permission failure does not poison the
        # caller's transaction (PendingRollbackError on later flushes).
        with session.begin_nested():
            event = AuditEvent(
                organisation_id=organisation_id,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id is not None else None,
                outcome=outcome_value,
                correlation_id=correlation_id,
                source=source,
                summary=sanitize_summary(summary),
                metadata_json=sanitize_metadata(metadata),
            )
            session.add(event)
            session.flush()
            return event
    except Exception:
        logger.exception("Failed to persist audit event action=%s", action)
        if raise_on_error:
            raise
        return None
    finally:
        _RECORDING = False


def record_event_independent(
    *,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | str | None = None,
    organisation_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    actor_role: str | None = None,
    outcome: AuditOutcome | str = AuditOutcome.DENIED,
    correlation_id: str | None = None,
    source: str | None = "api",
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent | None:
    """Commit an audit event on its own connection (survives request rollback).

    Used for access-denied / auth-failure paths that raise after recording.
    Platform-null organisation rows require RLS bypass; org-scoped rows set
    ``app.organisation_id``. Failures are logged and never raised to callers.
    """
    session = None
    try:
        from app.db.session import get_session_factory
        from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

        session = get_session_factory()()
        if organisation_id is None:
            apply_platform_rls_bypass(session)
        else:
            apply_organisation_rls(session, organisation_id)
        event = record_event(
            session,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            organisation_id=organisation_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            outcome=outcome,
            correlation_id=correlation_id,
            source=source,
            summary=summary,
            metadata=metadata,
            raise_on_error=True,
        )
        session.commit()
        return event
    except Exception:
        if session is not None:
            session.rollback()
        logger.exception("Independent audit commit failed action=%s", action)
        return None
    finally:
        if session is not None:
            session.close()
