"""RBAC for F6.6 finance module."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_finance_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenants cannot access finance records")
    if ctx.authorization.has_permission(Permission.FINANCE_RECORDS_READ):
        return
    if ctx.authorization.has_permission(Permission.FINANCE_RECORDS_MANAGE):
        return
    if ctx.authorization.has_permission(Permission.FINANCE_REPORTS_VIEW):
        return
    require_permission(ctx.authorization, Permission.FINANCE_RECORDS_READ)


def require_finance_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.FINANCE_RECORDS_MANAGE)


def require_budget_read(ctx: OrganisationContext) -> None:
    if ctx.authorization.has_permission(Permission.FINANCE_BUDGETS_READ):
        return
    if ctx.authorization.has_permission(Permission.FINANCE_BUDGETS_MANAGE):
        return
    require_permission(ctx.authorization, Permission.FINANCE_BUDGETS_READ)


def require_budget_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.FINANCE_BUDGETS_MANAGE)


def require_finance_export(ctx: OrganisationContext) -> None:
    if ctx.authorization.has_permission(Permission.FINANCE_EXPORTS):
        return
    if ctx.authorization.has_permission(Permission.REPORTS_EXPORT_CSV):
        return
    require_permission(ctx.authorization, Permission.FINANCE_EXPORTS)
