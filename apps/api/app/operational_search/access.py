"""RBAC for operational natural-language search."""

from __future__ import annotations

from fastapi import HTTPException

from app.db.models.enums import HMoreRole
from app.operational_search.catalog import ENTITY_PERMISSIONS
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_search(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.TENANT:
        raise HTTPException(status_code=403, detail="Operational search is not available for this role")
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.OPERATIONAL_SEARCH_RUN)


def entity_allowed(ctx: OrganisationContext, entity: str) -> bool:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return True
    needed = ENTITY_PERMISSIONS.get(entity, ())
    return any(ctx.authorization.has_permission(permission) for permission in needed)


def org_wide(ctx: OrganisationContext, entity: str) -> bool:
    from app.operational_search.catalog import ORG_WIDE_PERMISSIONS

    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return True
    return any(ctx.authorization.has_permission(permission) for permission in ORG_WIDE_PERMISSIONS.get(entity, ()))
