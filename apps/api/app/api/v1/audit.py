from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.query import get_audit_event_for_org, list_for_org_context, list_for_platform
from app.audit.service import AuditOutcome, record_event
from app.db.session import get_session
from app.rbac.context import AuthorizationContext
from app.rbac.deps import require_perm
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context, get_platform_context

router = APIRouter(prefix="/audit-events", tags=["audit"])


def _serialize(event) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "organisation_id": str(event.organisation_id) if event.organisation_id else None,
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "actor_role": event.actor_role,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "outcome": event.outcome,
        "correlation_id": event.correlation_id,
        "source": event.source,
        "summary": event.summary,
        "metadata": event.metadata_json,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("")
def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    outcome: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    _authz: AuthorizationContext = Depends(require_perm(Permission.AUDIT_LOGS_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = list_for_org_context(
        session,
        org,
        page=page,
        page_size=page_size,
        action=action,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        created_from=created_from,
        created_to=created_to,
    )
    record_event(
        session,
        action=audit_events.AUDIT_READ,
        resource_type="audit_events",
        organisation_id=org.organisation_id,
        actor_user_id=org.user_id,
        actor_role=org.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Listed organisation audit events",
        metadata={"page": page, "total": total},
        raise_on_error=False,
    )
    return {
        "items": [_serialize(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/platform")
def list_platform_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    organisation_id: uuid.UUID | None = None,
    action: str | None = None,
    outcome: str | None = None,
    authz: AuthorizationContext = Depends(get_platform_context),
    _perm: AuthorizationContext = Depends(require_perm(Permission.AUDIT_LOGS_READ)),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = list_for_platform(
        session,
        authz,
        organisation_id=organisation_id,
        page=page,
        page_size=page_size,
        action=action,
        outcome=outcome,
    )
    return {
        "items": [_serialize(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{event_id}")
def get_event(
    event_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(require_perm(Permission.AUDIT_LOGS_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    event = get_audit_event_for_org(session, org.organisation_id, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _serialize(event)
