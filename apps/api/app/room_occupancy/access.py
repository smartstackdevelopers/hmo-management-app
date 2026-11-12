"""RBAC helpers for F6.5 room occupancy."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_occupancy_read(ctx: OrganisationContext) -> None:
    if ctx.authorization.has_permission(Permission.OCCUPANCY_READ):
        return
    if ctx.authorization.has_permission(Permission.OCCUPANCY_ALERTS_MANAGE):
        return
    if ctx.authorization.has_permission(Permission.OCCUPANCY_SETTINGS_MANAGE):
        return
    require_permission(ctx.authorization, Permission.OCCUPANCY_READ)


def require_occupancy_settings(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.OCCUPANCY_SETTINGS_MANAGE)


def require_occupancy_alerts_manage(ctx: OrganisationContext) -> None:
    if ctx.authorization.has_permission(Permission.OCCUPANCY_ALERTS_MANAGE):
        return
    if ctx.authorization.has_permission(Permission.OCCUPANCY_SETTINGS_MANAGE):
        return
    require_permission(ctx.authorization, Permission.OCCUPANCY_ALERTS_MANAGE)


def require_occupancy_correct(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.OCCUPANCY_COUNTS_CORRECT)


def deny_tenant_and_unauthorised_landlord(ctx: OrganisationContext) -> None:
    """Tenants never see live occupancy; landlords need explicit occupancy.read."""
    from app.db.models.enums import HMoreRole

    if ctx.role == HMoreRole.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenants cannot access room occupancy")
    require_occupancy_read(ctx)
