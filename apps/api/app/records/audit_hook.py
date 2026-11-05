"""Lightweight CRUD audit write into audit_events.

F1.7 owns the full audit framework. This helper only inserts durable rows into the
existing F1.2 table so Phase 1 acceptance can record create/update/archive actions.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

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
) -> AuditEvent:
    event = AuditEvent(
        organisation_id=organisation_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        summary=summary,
        metadata_json=metadata,
    )
    session.add(event)
    session.flush()
    return event
