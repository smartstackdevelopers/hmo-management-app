"""Authorization service: permission checks and resource-scope helpers."""

from __future__ import annotations

import uuid

from app.auth.tokens import http_403
from app.db.models.enums import HMoreRole
from app.rbac.context import AuthorizationContext
from app.rbac.permissions import Permission, parse_permission


def require_permission(ctx: AuthorizationContext, permission: Permission | str) -> None:
    required = permission if isinstance(permission, Permission) else parse_permission(permission)
    if not ctx.has_permission(required):
        raise http_403(f"Missing permission: {required.value}")


def assert_same_user(ctx: AuthorizationContext, resource_user_id: uuid.UUID) -> None:
    if ctx.user.id != resource_user_id:
        raise http_403("Access limited to own records")


def assert_landlord_property_access(
    ctx: AuthorizationContext,
    *,
    property_organisation_id: uuid.UUID,
    landlord_user_id: uuid.UUID | None,
) -> None:
    """Landlord may access own properties; Org Admin may read org properties with permission."""
    if ctx.active_role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.active_organisation_id != property_organisation_id:
        # F1.5 will harden org isolation; F1.4 still rejects cross-org property access here.
        raise http_403("Property is outside the active organisation")
    if ctx.active_role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx, Permission.PROPERTIES_READ)
        return
    if ctx.active_role == HMoreRole.LANDLORD:
        require_permission(ctx, Permission.PROPERTIES_MANAGE)
        if landlord_user_id != ctx.user.id:
            raise http_403("Landlord may only manage own properties")
        return
    raise http_403("Not permitted to access this property")


def assert_assigned_work_order(
    ctx: AuthorizationContext,
    *,
    organisation_id: uuid.UUID,
    assignee_user_id: uuid.UUID | None,
) -> None:
    if ctx.active_role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.active_organisation_id != organisation_id:
        raise http_403("Work order is outside the active organisation")
    if ctx.active_role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx, Permission.WORK_ORDERS_APPROVE_ASSIGNED)
        return
    if ctx.active_role == HMoreRole.MAINTENANCE_CONTRACTOR:
        require_permission(ctx, Permission.WORK_ORDERS_READ_ASSIGNED)
        if assignee_user_id != ctx.user.id:
            raise http_403("Contractor may only access assigned work orders")
        return
    raise http_403("Not permitted to access this work order")


def assert_assigned_support_caseload(
    ctx: AuthorizationContext,
    *,
    organisation_id: uuid.UUID,
    assigned_support_worker_id: uuid.UUID | None,
) -> None:
    if ctx.active_role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.active_organisation_id != organisation_id:
        raise http_403("Record is outside the active organisation")
    if ctx.active_role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx, Permission.ORGANISATION_USERS_READ)
        return
    if ctx.active_role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx, Permission.SUPPORT_NOTES_READ_ASSIGNED)
        if assigned_support_worker_id != ctx.user.id:
            raise http_403("Support Worker may only access assigned caseload")
        return
    raise http_403("Not permitted to access this support record")
