"""F7.3 backup administration RBAC."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_backup_read(ctx: OrganisationContext) -> None:
    if ctx.authorization.has_permission(Permission.BACKUP_READ):
        return
    if ctx.authorization.has_permission(Permission.BACKUP_MANAGE):
        return
    require_permission(ctx.authorization, Permission.BACKUP_READ)


def require_backup_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.BACKUP_MANAGE)


def require_restore_drill(ctx: OrganisationContext) -> None:
    if ctx.role != HMoreRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Restore drills are restricted to Super Admin",
        )
    require_permission(ctx.authorization, Permission.BACKUP_RESTORE_DRILL)
