"""F8.8 tenant engagement access."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_READ)


def assert_tenant_or_staff(
    ctx: OrganisationContext, tenant_user_id: UUID, *, staff_ok: bool = True
) -> None:
    if ctx.user_id == tenant_user_id or ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if staff_ok and ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_STAFF)
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorised for this tenant engagement record")
