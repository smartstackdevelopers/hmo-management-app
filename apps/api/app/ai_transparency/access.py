"""RBAC helpers for F3.14 AI activity transparency."""

from __future__ import annotations

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_activity_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_ACTIVITY_READ)


def require_feedback_submit(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_ACTIVITY_FEEDBACK_SUBMIT)


def require_feedback_review(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_ACTIVITY_FEEDBACK_REVIEW)


def is_tenant_role(ctx: OrganisationContext) -> bool:
    return ctx.role == HMoreRole.TENANT


def can_view_staff_activity(ctx: OrganisationContext) -> bool:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return True
    if is_tenant_role(ctx):
        return False
    return ctx.authorization.has_permission(Permission.AI_ACTIVITY_READ)
