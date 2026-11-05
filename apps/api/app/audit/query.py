"""Authorised read access to audit events."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models.audit import AuditEvent
from app.records.pagination import offset_limit
from app.rbac.context import AuthorizationContext
from app.tenancy.context import OrganisationContext


def _org_stmt(organisation_id: uuid.UUID) -> Select[tuple[AuditEvent]]:
    return select(AuditEvent).where(AuditEvent.organisation_id == organisation_id)


def list_audit_events(
    session: Session,
    *,
    organisation_id: uuid.UUID | None,
    page: int,
    page_size: int,
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    outcome: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    platform_wide: bool = False,
) -> tuple[list[AuditEvent], int]:
    if platform_wide:
        stmt = select(AuditEvent)
        if organisation_id is not None:
            stmt = stmt.where(AuditEvent.organisation_id == organisation_id)
    else:
        if organisation_id is None:
            return [], 0
        stmt = _org_stmt(organisation_id)

    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if actor_user_id:
        stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
    if resource_type:
        stmt = stmt.where(AuditEvent.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditEvent.resource_id == resource_id)
    if outcome:
        stmt = stmt.where(AuditEvent.outcome == outcome)
    if created_from:
        stmt = stmt.where(AuditEvent.created_at >= created_from)
    if created_to:
        stmt = stmt.where(AuditEvent.created_at <= created_to)

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(
            stmt.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return rows, total


def get_audit_event_for_org(
    session: Session, organisation_id: uuid.UUID, event_id: uuid.UUID
) -> AuditEvent | None:
    event = session.get(AuditEvent, event_id)
    if event is None:
        return None
    if event.organisation_id != organisation_id:
        return None
    return event


def list_for_org_context(
    session: Session,
    ctx: OrganisationContext,
    **kwargs,
) -> tuple[list[AuditEvent], int]:
    return list_audit_events(
        session, organisation_id=ctx.organisation_id, platform_wide=False, **kwargs
    )


def list_for_platform(
    session: Session,
    _authz: AuthorizationContext,
    **kwargs,
) -> tuple[list[AuditEvent], int]:
    return list_audit_events(session, platform_wide=True, **kwargs)
