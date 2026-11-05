from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.session_policy import session_policy_payload
from app.auth.tokens import http_403
from app.db.session import get_session
from app.rbac.assignment import assign_membership
from app.rbac.context import AuthorizationContext
from app.rbac.deps import get_authorization_context, require_perm
from app.rbac.matrix import ROLE_PERMISSIONS
from app.rbac.permissions import PERMISSION_CATALOG, Permission
from app.rbac.roles import ROLE_DEFINITIONS
from app.rbac.service import (
    assert_assigned_support_caseload,
    assert_assigned_work_order,
    assert_landlord_property_access,
    assert_same_user,
)

router = APIRouter(prefix="/rbac", tags=["rbac"])


class AssignMembershipBody(BaseModel):
    user_id: uuid.UUID
    role: str = Field(min_length=1, max_length=64)
    organisation_id: uuid.UUID | None = None


class ResourceProbeBody(BaseModel):
    organisation_id: uuid.UUID
    landlord_user_id: uuid.UUID | None = None
    assignee_user_id: uuid.UUID | None = None
    assigned_support_worker_id: uuid.UUID | None = None
    resource_user_id: uuid.UUID | None = None


@router.get("/roles")
def list_roles(
    _ctx: AuthorizationContext = Depends(get_authorization_context),
) -> dict[str, Any]:
    return {
        "count": len(ROLE_DEFINITIONS),
        "roles": [
            {
                "id": definition.role.value,
                "display_name": definition.display_name,
                "platform_scoped": definition.platform_scoped,
                "responsibilities": list(definition.responsibilities),
            }
            for definition in ROLE_DEFINITIONS.values()
        ],
    }


@router.get("/permissions")
def list_permissions(
    _ctx: AuthorizationContext = Depends(get_authorization_context),
) -> dict[str, Any]:
    return {
        "permissions": [
            {
                "id": meta.permission.value,
                "purpose": meta.purpose,
                "sensitive": meta.sensitive,
            }
            for meta in PERMISSION_CATALOG.values()
        ]
    }


@router.get("/matrix")
def permission_matrix(
    ctx: AuthorizationContext = Depends(require_perm(Permission.AUDIT_LOGS_READ)),
) -> dict[str, Any]:
    return {
        "roles": {
            role.value: sorted(p.value for p in perms)
            for role, perms in ROLE_PERMISSIONS.items()
        },
        "viewer": {
            "user_id": str(ctx.user.id),
            "active_role": ctx.active_role.value if ctx.active_role else None,
        },
    }


@router.get("/me")
def my_authorization(
    ctx: AuthorizationContext = Depends(get_authorization_context),
) -> dict[str, Any]:
    return {
        "user_id": str(ctx.user.id),
        "external_subject": ctx.user.external_subject,
        "authorization_version": ctx.authorization_version,
        "active_role": ctx.active_role.value if ctx.active_role else None,
        "active_organisation_id": (
            str(ctx.active_organisation_id) if ctx.active_organisation_id else None
        ),
        "memberships": [
            {
                "id": str(m.membership_id),
                "role": m.role.value,
                "organisation_id": str(m.organisation_id) if m.organisation_id else None,
                "status": m.status.value,
            }
            for m in ctx.memberships
        ],
        "permissions": sorted(p.value for p in ctx.permissions()),
        "session": session_policy_payload(ctx),
    }


@router.get("/session")
def session_control(
    ctx: AuthorizationContext = Depends(get_authorization_context),
) -> dict[str, Any]:
    return session_policy_payload(ctx)


@router.post("/memberships")
def create_or_update_membership(
    body: AssignMembershipBody,
    ctx: AuthorizationContext = Depends(get_authorization_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        membership = assign_membership(
            session,
            actor=ctx,
            target_user_id=body.user_id,
            role_value=body.role,
            organisation_id=body.organisation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "id": str(membership.id),
        "user_id": str(membership.user_id),
        "role": membership.role.value,
        "organisation_id": (
            str(membership.organisation_id) if membership.organisation_id else None
        ),
        "status": membership.status.value,
    }


@router.get("/gates/organisations.manage")
def gate_organisations_manage(
    ctx: AuthorizationContext = Depends(require_perm(Permission.ORGANISATIONS_MANAGE)),
) -> dict[str, str]:
    return {"status": "ok", "permission": Permission.ORGANISATIONS_MANAGE.value}


@router.get("/gates/audit_logs.read")
def gate_audit_logs(
    ctx: AuthorizationContext = Depends(require_perm(Permission.AUDIT_LOGS_READ)),
) -> dict[str, str]:
    return {"status": "ok", "permission": Permission.AUDIT_LOGS_READ.value}


@router.get("/gates/properties.manage")
def gate_properties_manage(
    ctx: AuthorizationContext = Depends(require_perm(Permission.PROPERTIES_MANAGE)),
) -> dict[str, str]:
    return {"status": "ok", "permission": Permission.PROPERTIES_MANAGE.value}


@router.post("/gates/property-access")
def gate_property_access(
    body: ResourceProbeBody,
    ctx: AuthorizationContext = Depends(get_authorization_context),
) -> dict[str, str]:
    assert_landlord_property_access(
        ctx,
        property_organisation_id=body.organisation_id,
        landlord_user_id=body.landlord_user_id,
    )
    return {"status": "ok"}


@router.post("/gates/work-order-access")
def gate_work_order_access(
    body: ResourceProbeBody,
    ctx: AuthorizationContext = Depends(get_authorization_context),
) -> dict[str, str]:
    assert_assigned_work_order(
        ctx,
        organisation_id=body.organisation_id,
        assignee_user_id=body.assignee_user_id,
    )
    return {"status": "ok"}


@router.post("/gates/support-access")
def gate_support_access(
    body: ResourceProbeBody,
    ctx: AuthorizationContext = Depends(get_authorization_context),
) -> dict[str, str]:
    assert_assigned_support_caseload(
        ctx,
        organisation_id=body.organisation_id,
        assigned_support_worker_id=body.assigned_support_worker_id,
    )
    return {"status": "ok"}


@router.post("/gates/own-profile")
def gate_own_profile(
    body: ResourceProbeBody,
    ctx: AuthorizationContext = Depends(require_perm(Permission.PROFILE_READ_OWN)),
) -> dict[str, str]:
    if body.resource_user_id is None:
        raise http_403("resource_user_id is required")
    assert_same_user(ctx, body.resource_user_id)
    return {"status": "ok"}
