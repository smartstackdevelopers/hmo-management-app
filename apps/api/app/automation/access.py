"""RBAC for F6.3 automation."""

from __future__ import annotations

from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_rules_read(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.AUTOMATION_RULES_READ)


def require_rules_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.AUTOMATION_RULES_MANAGE)


def require_runs_read(ctx: OrganisationContext) -> None:
    # Manage implies read; allow either.
    if ctx.authorization.has_permission(Permission.AUTOMATION_RUNS_READ):
        return
    if ctx.authorization.has_permission(Permission.AUTOMATION_RULES_MANAGE):
        return
    require_permission(ctx.authorization, Permission.AUTOMATION_RUNS_READ)


def require_escalations_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.AUTOMATION_ESCALATIONS_MANAGE)
