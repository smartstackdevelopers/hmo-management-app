"""RBAC for F7.2 privacy management."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_privacy_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenants cannot access privacy management")
    if ctx.authorization.has_permission(Permission.PRIVACY_READ):
        return
    if ctx.authorization.has_permission(Permission.PRIVACY_MANAGE):
        return
    require_permission(ctx.authorization, Permission.PRIVACY_READ)


def require_privacy_manage(ctx: OrganisationContext) -> None:
    if ctx.role in {HMoreRole.TENANT, HMoreRole.LANDLORD, HMoreRole.MAINTENANCE_CONTRACTOR}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authorised administrators may manage privacy records",
        )
    require_permission(ctx.authorization, Permission.PRIVACY_MANAGE)
