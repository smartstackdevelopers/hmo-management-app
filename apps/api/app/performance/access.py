"""F7.4 performance benchmark RBAC."""

from __future__ import annotations

from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_performance_read(ctx: OrganisationContext) -> None:
    if ctx.authorization.has_permission(Permission.PERFORMANCE_READ):
        return
    if ctx.authorization.has_permission(Permission.PERFORMANCE_BENCHMARK_RUN):
        return
    if ctx.authorization.has_permission(Permission.PLATFORM_MONITORING_READ):
        return
    require_permission(ctx.authorization, Permission.PERFORMANCE_READ)


def require_performance_run(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.PERFORMANCE_BENCHMARK_RUN)
