"""RBAC for F3.11 duplicate detection."""

from __future__ import annotations

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_run(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.DUPLICATE_DETECTION_RUN)


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.DUPLICATE_DETECTION_READ)


def require_review(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.DUPLICATE_DETECTION_REVIEW)
