"""RBAC for F6.4 Integration Hub."""

from __future__ import annotations

from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_integrations_read(ctx: OrganisationContext) -> None:
    if ctx.authorization.has_permission(Permission.INTEGRATIONS_READ):
        return
    if ctx.authorization.has_permission(Permission.INTEGRATIONS_MANAGE):
        return
    require_permission(ctx.authorization, Permission.INTEGRATIONS_READ)


def require_integrations_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.INTEGRATIONS_MANAGE)
