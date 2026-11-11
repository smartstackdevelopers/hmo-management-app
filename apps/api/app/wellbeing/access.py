"""Tenant ownership for private wellbeing records; staff only manage resources."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.records.tenant_service import find_own_tenant
from app.tenancy.context import OrganisationContext


def resolve_own_tenant(session: Session, ctx: OrganisationContext) -> Tenant:
    if ctx.role != HMoreRole.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant role required")
    if not ctx.authorization.has_permission(Permission.WELLBEING_MANAGE_OWN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {Permission.WELLBEING_MANAGE_OWN.value}",
        )
    tenant = find_own_tenant(session, ctx)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No linked tenant profile")
    return tenant


def require_resource_admin(ctx: OrganisationContext) -> None:
    if ctx.authorization.has_permission(Permission.WELLBEING_RESOURCES_MANAGE):
        return
    if ctx.authorization.has_permission(Permission.TENANTS_MANAGE):
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wellbeing resource admin required")
