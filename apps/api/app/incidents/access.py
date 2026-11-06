"""Authorisation for F2.4 incidents and workload."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.incidents import Incident
from app.db.models.membership import OrganisationMembership
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access
from app.tenancy.context import OrganisationContext


def require_incident_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.INCIDENTS_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_incident_create(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.INCIDENTS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.INCIDENTS_CREATE_ASSIGNED)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_incident_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.INCIDENTS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.INCIDENTS_READ_ASSIGNED)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_workload_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.WORKLOAD_READ)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.WORKLOAD_READ_OWN)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_active_org_member(
    session: Session, *, organisation_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    membership = session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.user_id == user_id,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not an active member of this organisation",
        )


def assert_incident_links(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: uuid.UUID | None,
    property_id: uuid.UUID | None,
    room_id: uuid.UUID | None,
) -> None:
    if tenant_id is not None:
        tenant = session.get(Tenant, tenant_id)
        if tenant is None or tenant.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        if ctx.role == HMoreRole.SUPPORT_WORKER:
            assert_tenant_support_access(session, ctx, tenant_id)
    if property_id is not None:
        prop = session.get(Property, property_id)
        if prop is None or prop.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    if room_id is not None:
        room = session.get(Room, room_id)
        if room is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        if property_id is not None and room.property_id != property_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room/property mismatch")
        prop = session.get(Property, room.property_id)
        if prop is None or prop.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")


def assert_can_view_incident(ctx: OrganisationContext, incident: Incident) -> None:
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        if incident.reported_by_user_id == ctx.user_id or incident.reviewer_user_id == ctx.user_id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
