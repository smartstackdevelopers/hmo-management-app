"""Permission helpers for occupancy surveys — reuse existing occupancy/inspection perms."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.rbac.context import AuthorizationContext
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def require_survey_read(ctx: OrganisationContext | AuthorizationContext) -> None:
    authz = ctx.authorization if isinstance(ctx, OrganisationContext) else ctx
    if authz.has_permission(Permission.OCCUPANCY_READ):
        return
    if authz.has_permission(Permission.OCCUPANCY_ALERTS_MANAGE):
        return
    if authz.has_permission(Permission.INSPECTIONS_MANAGE):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Missing permission to read occupancy surveys",
    )


def require_survey_write(ctx: OrganisationContext | AuthorizationContext) -> None:
    authz = ctx.authorization if isinstance(ctx, OrganisationContext) else ctx
    if authz.has_permission(Permission.OCCUPANCY_ALERTS_MANAGE):
        return
    if authz.has_permission(Permission.INSPECTIONS_MANAGE):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Missing permission to manage occupancy surveys",
    )
