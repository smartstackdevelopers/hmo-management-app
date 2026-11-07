"""RBAC helpers for AI budget and cost dashboard access (F3.3)."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def require_ai_budget_read(ctx: OrganisationContext) -> None:
    if not ctx.authorization.has_permission(Permission.AI_BUDGET_READ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI budget read denied")


def require_ai_budget_manage(ctx: OrganisationContext) -> None:
    if not ctx.authorization.has_permission(Permission.AI_BUDGET_MANAGE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI budget manage denied")


def require_ai_usage_read(ctx: OrganisationContext) -> None:
    if not ctx.authorization.has_permission(Permission.AI_USAGE_READ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI usage read denied")


def require_ai_cost_dashboard(ctx: OrganisationContext) -> None:
    if not ctx.authorization.has_permission(Permission.AI_COST_DASHBOARD_VIEW):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI cost dashboard denied")


def require_ai_pricing_manage(ctx: OrganisationContext) -> None:
    if not ctx.authorization.has_permission(Permission.AI_PRICING_MANAGE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI pricing manage denied")


def require_platform_ai_dashboard(role: HMoreRole) -> None:
    if role != HMoreRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform AI cost dashboard requires Super Admin",
        )
