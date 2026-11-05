"""Compatibility wrapper — F1.6 CRUD callers use the F1.7 central audit service."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.audit.service import AuditOutcome, record_event
from app.db.models.audit import AuditEvent


def record_crud_event(
    session: Session,
    *,
    organisation_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | str | None,
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
    actor_role: str | None = None,
    outcome: str = AuditOutcome.SUCCESS.value,
    correlation_id: str | None = None,
) -> AuditEvent | None:
    return record_event(
        session,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        organisation_id=organisation_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        outcome=outcome,
        correlation_id=correlation_id,
        summary=summary,
        metadata=metadata,
    )
