"""RBAC for F3.9 Compliance Agent."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_run(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.authorization.has_permission(Permission.AI_COMPLIANCE_RUN):
        return
    if ctx.authorization.has_permission(Permission.COMPLIANCE_CHECK):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permission: ai.compliance.run")


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.authorization.has_permission(Permission.AI_COMPLIANCE_READ):
        return
    if ctx.authorization.has_permission(Permission.COMPLIANCE_CHECK):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permission: ai.compliance.read")


def require_review(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_COMPLIANCE_REVIEW)
