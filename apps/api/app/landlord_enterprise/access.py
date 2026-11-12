"""Landlord enterprise access: property ownership + existing permissions."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.tokens import http_403
from app.db.models.enums import HMoreRole, RecordStatus
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


# F6.1 enterprise portfolio/rent/inspection surfaces — not every role with properties.read.
_LANDLORD_ENTERPRISE_ROLES = frozenset(
    {
        HMoreRole.LANDLORD,
        HMoreRole.ORGANISATION_ADMIN,
        HMoreRole.SUPER_ADMIN,
    }
)


def require_landlord_enterprise_read(ctx: OrganisationContext) -> None:
    """Restrict F6.1 reads to landlord / org admin / super admin.

    Support workers and maintenance contractors often hold ``properties.read`` for
    operational work; they must not pull landlord rent/portfolio dashboards via API.
    Super Admin may oversee when an organisation context is already established.
    """
    if ctx.role not in _LANDLORD_ENTERPRISE_ROLES:
        raise http_403("Landlord enterprise access is limited to landlord and organisation administrators")
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.authorization.has_permission(Permission.PROPERTIES_READ) or ctx.authorization.has_permission(
        Permission.PROPERTIES_MANAGE
    ):
        return
    raise http_403(f"Missing permission: {Permission.PROPERTIES_READ.value}")


def require_rent_manage(ctx: OrganisationContext) -> None:
    if not ctx.authorization.has_permission(Permission.RENT_RECORDS_MANAGE):
        raise http_403(f"Missing permission: {Permission.RENT_RECORDS_MANAGE.value}")


def require_inspections_manage(ctx: OrganisationContext) -> None:
    if not ctx.authorization.has_permission(Permission.INSPECTIONS_MANAGE):
        raise http_403(f"Missing permission: {Permission.INSPECTIONS_MANAGE.value}")


def require_repairs_read(ctx: OrganisationContext) -> None:
    if ctx.authorization.has_permission(Permission.REPAIRS_STATUS_READ) or ctx.authorization.has_permission(
        Permission.MAINTENANCE_READ_PROPERTY
    ):
        return
    raise http_403(f"Missing permission: {Permission.REPAIRS_STATUS_READ.value}")


def landlord_property_filter(ctx: OrganisationContext):
    """SQLAlchemy filter limiting landlords to properties they own.

    Unassigned properties (``landlord_user_id IS NULL``) are visible to organisation
    admins only — not to every landlord in the organisation.
    """
    if ctx.role == HMoreRole.LANDLORD:
        return Property.landlord_user_id == ctx.user_id
    return True


def list_accessible_property_ids(session: Session, ctx: OrganisationContext) -> list[uuid.UUID]:
    require_landlord_enterprise_read(ctx)
    stmt = select(Property.id).where(
        Property.organisation_id == ctx.organisation_id,
        Property.status == RecordStatus.ACTIVE,
        landlord_property_filter(ctx),
    )
    return list(session.scalars(stmt).all())


def get_accessible_property(session: Session, ctx: OrganisationContext, property_id: uuid.UUID) -> Property:
    require_landlord_enterprise_read(ctx)
    row = session.get(Property, property_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Property not found")
    if ctx.role == HMoreRole.LANDLORD:
        if row.landlord_user_id != ctx.user_id:
            raise http_403("Landlord may only access own properties")
    return row


def assert_room_on_property(session: Session, ctx: OrganisationContext, room_id: uuid.UUID, property_id: uuid.UUID) -> Room:
    room = session.get(Room, room_id)
    if room is None or room.organisation_id != ctx.organisation_id or room.property_id != property_id:
        raise HTTPException(status_code=404, detail="Room not found on property")
    return room


def assert_tenant_on_property(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, property_id: uuid.UUID
) -> Tenant:
    tenant = session.get(Tenant, tenant_id)
    if tenant is None or tenant.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if tenant.assigned_property_id is not None and tenant.assigned_property_id != property_id:
        raise HTTPException(status_code=422, detail="Tenant is not assigned to this property")
    # Landlords must not see tenants on other landlords' properties via loose assignment
    get_accessible_property(session, ctx, property_id)
    return tenant
