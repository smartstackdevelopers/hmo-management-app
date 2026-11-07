"""Authorisation for F2.8 maintenance."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.file_metadata import FileMetadata
from app.db.models.maintenance import MaintenanceRequest, MaintenanceRequestFile
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access
from app.tenancy.context import OrganisationContext


def require_maintenance_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_maintenance_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_MANAGE)
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.MAINTENANCE_READ_OWN)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.MAINTENANCE_READ_ASSIGNED)
        return
    if ctx.role == HMoreRole.LANDLORD:
        require_permission(ctx.authorization, Permission.MAINTENANCE_READ_PROPERTY)
        return
    if ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR:
        require_permission(ctx.authorization, Permission.MAINTENANCE_READ_ASSIGNED)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_maintenance_create(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_MANAGE)
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.MAINTENANCE_CREATE_OWN)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.MAINTENANCE_CREATE_ASSIGNED)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def resolve_own_tenant_id(session: Session, ctx: OrganisationContext) -> uuid.UUID | None:
    tenant = session.scalar(
        select(Tenant).where(
            Tenant.organisation_id == ctx.organisation_id,
            Tenant.user_id == ctx.user_id,
        )
    )
    return tenant.id if tenant else None


def assert_can_view_request(session: Session, ctx: OrganisationContext, row: MaintenanceRequest) -> None:
    require_maintenance_read(ctx)
    if row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")

    prop = session.get(Property, row.property_id)
    if prop is None or prop.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")

    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        return

    if ctx.role == HMoreRole.TENANT:
        own = resolve_own_tenant_id(session, ctx)
        if own is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if row.tenant_id != own and row.reported_by_user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")
        return

    if ctx.role == HMoreRole.LANDLORD:
        if prop.landlord_user_id is not None and prop.landlord_user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")
        return

    if ctx.role == HMoreRole.SUPPORT_WORKER:
        if row.tenant_id is not None:
            assert_tenant_support_access(session, ctx, row.tenant_id)
            return
        if row.assigned_user_id == ctx.user_id:
            return
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")

    if ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR:
        if row.assigned_user_id == ctx.user_id:
            return
        from app.db.models.maintenance import MaintenanceVisit

        has_visit = session.scalar(
            select(MaintenanceVisit).where(
                MaintenanceVisit.request_id == row.id,
                MaintenanceVisit.assignee_user_id == ctx.user_id,
            )
        )
        if has_visit is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_room_belongs(session: Session, property_id: uuid.UUID, room_id: uuid.UUID | None) -> None:
    if room_id is None:
        return
    room = session.get(Room, room_id)
    if room is None or room.property_id != property_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room does not belong to property")


def assert_can_access_maintenance_photo(
    session: Session, ctx: OrganisationContext, request_id: uuid.UUID, file_id: uuid.UUID
) -> None:
    """Enforce MAINTENANCE_PHOTO_READ plus request-level visibility (not FILES_READ alone)."""
    row = session.get(MaintenanceRequest, request_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")
    link = session.scalar(
        select(MaintenanceRequestFile).where(
            MaintenanceRequestFile.request_id == request_id,
            MaintenanceRequestFile.file_id == file_id,
        )
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not linked to this request")
    meta = session.get(FileMetadata, file_id)
    if meta is None or meta.organisation_id != ctx.organisation_id or meta.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.MAINTENANCE_PHOTO_READ)
    assert_can_view_request(session, ctx, row)
