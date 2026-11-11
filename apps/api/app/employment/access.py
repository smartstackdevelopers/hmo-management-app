"""Ownership and staff scope for employment preparation records."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.records.tenant_service import find_own_tenant
from app.tenancy.context import OrganisationContext


def require_employment_prep_permission(ctx: OrganisationContext) -> None:
    if ctx.authorization.has_permission(Permission.EMPLOYMENT_PREP_MANAGE_OWN):
        return
    if ctx.authorization.has_permission(Permission.EMPLOYMENT_SUPPORT_MANAGE_ASSIGNED):
        return
    if ctx.authorization.has_permission(Permission.EMPLOYMENT_PREP_READ_ASSIGNED):
        return
    if ctx.authorization.has_permission(Permission.TENANTS_MANAGE):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def resolve_own_tenant(session: Session, ctx: OrganisationContext) -> Tenant:
    if ctx.role != HMoreRole.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant role required")
    if not ctx.authorization.has_permission(Permission.EMPLOYMENT_PREP_MANAGE_OWN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {Permission.EMPLOYMENT_PREP_MANAGE_OWN.value}",
        )
    tenant = find_own_tenant(session, ctx)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No linked tenant profile")
    return tenant


def resolve_tenant_for_staff_or_self(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: uuid.UUID | None,
) -> Tenant:
    """Tenants always use their linked row. Staff must pass an in-org tenant id."""
    if ctx.role == HMoreRole.TENANT:
        return resolve_own_tenant(session, ctx)
    require_employment_prep_permission(ctx)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="tenant_id is required")
    tenant = session.get(Tenant, tenant_id)
    if tenant is None or tenant.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    # Support workers need assigned-scope permission; org admins use tenants.manage / employment read.
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        if not (
            ctx.authorization.has_permission(Permission.EMPLOYMENT_PREP_READ_ASSIGNED)
            or ctx.authorization.has_permission(Permission.EMPLOYMENT_SUPPORT_MANAGE_ASSIGNED)
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        from app.support.access import assert_tenant_support_access

        assert_tenant_support_access(session, ctx, tenant.id)
    return tenant
