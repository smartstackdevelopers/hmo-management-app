"""Organisation-aware query helpers. Deny cross-organisation access by default."""

from __future__ import annotations

import uuid
from typing import TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.auth.tokens import http_403
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.tenant import Tenant
from app.tenancy.context import OrganisationContext

T = TypeVar("T")


def assert_same_organisation(
    ctx: OrganisationContext,
    record_organisation_id: uuid.UUID | None,
) -> None:
    if record_organisation_id is None:
        raise http_403("Record is not organisation-scoped")
    if record_organisation_id != ctx.organisation_id:
        # Do not reveal whether the foreign record exists.
        raise http_403("Access denied")


def scope_query(stmt: Select[tuple[T]], organisation_id: uuid.UUID, column) -> Select[tuple[T]]:
    return stmt.where(column == organisation_id)


def list_properties_for_org(session: Session, ctx: OrganisationContext) -> list[Property]:
    stmt = scope_query(select(Property), ctx.organisation_id, Property.organisation_id)
    return list(session.scalars(stmt))


def get_property_for_org(
    session: Session,
    ctx: OrganisationContext,
    property_id: uuid.UUID,
) -> Property | None:
    property_row = session.get(Property, property_id)
    if property_row is None:
        return None
    if property_row.organisation_id != ctx.organisation_id:
        return None
    return property_row


def require_property_for_org(
    session: Session,
    ctx: OrganisationContext,
    property_id: uuid.UUID,
) -> Property:
    property_row = get_property_for_org(session, ctx, property_id)
    if property_row is None:
        raise http_403("Access denied")
    return property_row


def list_tenants_for_org(session: Session, ctx: OrganisationContext) -> list[Tenant]:
    stmt = scope_query(select(Tenant), ctx.organisation_id, Tenant.organisation_id)
    return list(session.scalars(stmt))


def get_tenant_for_org(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
) -> Tenant | None:
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        return None
    if tenant.organisation_id != ctx.organisation_id:
        return None
    return tenant


def require_tenant_for_org(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
) -> Tenant:
    tenant = get_tenant_for_org(session, ctx, tenant_id)
    if tenant is None:
        raise http_403("Access denied")
    return tenant


def list_rooms_for_org(session: Session, ctx: OrganisationContext) -> list[Room]:
    stmt = scope_query(select(Room), ctx.organisation_id, Room.organisation_id)
    return list(session.scalars(stmt))


def get_room_for_org(
    session: Session,
    ctx: OrganisationContext,
    room_id: uuid.UUID,
) -> Room | None:
    room = session.get(Room, room_id)
    if room is None:
        return None
    if room.organisation_id != ctx.organisation_id:
        return None
    return room


def require_room_for_org(
    session: Session,
    ctx: OrganisationContext,
    room_id: uuid.UUID,
) -> Room:
    room = get_room_for_org(session, ctx, room_id)
    if room is None:
        raise http_403("Access denied")
    return room


def create_property_for_org(
    session: Session,
    ctx: OrganisationContext,
    *,
    name: str,
    address_line1: str,
    city: str,
    postcode: str,
) -> Property:
    row = Property(
        organisation_id=ctx.organisation_id,
        name=name,
        address_line1=address_line1,
        city=city,
        postcode=postcode,
        landlord_user_id=ctx.user_id if ctx.role.value == "landlord" else None,
    )
    session.add(row)
    session.flush()
    return row


def update_property_for_org(
    session: Session,
    ctx: OrganisationContext,
    property_id: uuid.UUID,
    *,
    name: str | None = None,
) -> Property:
    row = require_property_for_org(session, ctx, property_id)
    if name is not None:
        row.name = name
    session.add(row)
    session.flush()
    return row


def delete_property_for_org(
    session: Session,
    ctx: OrganisationContext,
    property_id: uuid.UUID,
) -> None:
    row = require_property_for_org(session, ctx, property_id)
    # Rooms may block delete via FK; isolation probes use properties without rooms.
    session.delete(row)
    session.flush()
