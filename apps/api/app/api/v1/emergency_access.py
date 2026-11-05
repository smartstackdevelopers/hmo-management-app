"""Emergency access logging endpoints.

These endpoints create and transition grant *records* and audit events only.
They do not elevate RBAC permissions or bypass organisation isolation.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit.emergency import request_emergency_access, transition_emergency_access
from app.db.session import get_session
from app.rbac.context import AuthorizationContext
from app.rbac.deps import require_perm
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/emergency-access", tags=["emergency-access"])


class EmergencyRequestBody(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
    duration_hours: int = Field(default=4, ge=1, le=72)
    resource_type: str | None = Field(default=None, max_length=100)
    resource_id: str | None = Field(default=None, max_length=100)


class EmergencyTransitionBody(BaseModel):
    status: str = Field(min_length=1, max_length=32)


def _serialize(grant) -> dict[str, Any]:
    return {
        "id": str(grant.id),
        "organisation_id": str(grant.organisation_id),
        "actor_user_id": str(grant.actor_user_id),
        "status": grant.status,
        "reason": grant.reason,
        "resource_type": grant.resource_type,
        "resource_id": grant.resource_id,
        "approved_by_user_id": (
            str(grant.approved_by_user_id) if grant.approved_by_user_id else None
        ),
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "activated_at": grant.activated_at.isoformat() if grant.activated_at else None,
        "revoked_at": grant.revoked_at.isoformat() if grant.revoked_at else None,
        "created_at": grant.created_at.isoformat() if grant.created_at else None,
        "grants_permissions": False,
    }


@router.post("", status_code=201)
def create_request(
    body: EmergencyRequestBody,
    _authz: AuthorizationContext = Depends(require_perm(Permission.AUDIT_LOGS_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-Id"),
) -> dict[str, Any]:
    """Record an emergency-access request. Does not grant elevated access."""
    grant = request_emergency_access(
        session,
        org,
        reason=body.reason,
        duration_hours=body.duration_hours,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        correlation_id=x_correlation_id,
    )
    return _serialize(grant)


@router.patch("/{grant_id}")
def transition(
    grant_id: uuid.UUID,
    body: EmergencyTransitionBody,
    _authz: AuthorizationContext = Depends(require_perm(Permission.AUDIT_LOGS_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-Id"),
) -> dict[str, Any]:
    grant = transition_emergency_access(
        session,
        org,
        grant_id,
        new_status=body.status,
        correlation_id=x_correlation_id,
    )
    return _serialize(grant)
