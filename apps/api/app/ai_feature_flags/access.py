"""RBAC for F3.15 AI feature flag administration."""

from __future__ import annotations

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_FEATURE_FLAGS_READ)


def require_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_FEATURE_FLAGS_MANAGE)
