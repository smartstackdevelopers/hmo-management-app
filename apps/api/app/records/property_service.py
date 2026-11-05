from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, RecordStatus
from app.db.models.property import Property
from app.db.models.room import Room
from app.records.audit_hook import record_crud_event
from app.records.pagination import offset_limit
from app.records.schemas import PropertyCreate, PropertyUpdate
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import require_property_for_org


def _assert_landlord_scope(ctx: OrganisationContext, property_row: Property) -> None:
    if ctx.role != HMoreRole.LANDLORD:
        return
    if property_row.landlord_user_id is None:
        return
    if property_row.landlord_user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def create_property(session: Session, ctx: OrganisationContext, data: PropertyCreate) -> Property:
    landlord_user_id = data.landlord_user_id
    if ctx.role == HMoreRole.LANDLORD:
        landlord_user_id = ctx.user_id
    row = Property(
        organisation_id=ctx.organisation_id,
        name=data.name.strip(),
        address_line1=data.address_line1.strip(),
        address_line2=data.address_line2,
        city=data.city.strip(),
        region=data.region,
        postcode=data.postcode.strip(),
        country_code=data.country_code.upper(),
        landlord_user_id=landlord_user_id,
        notes=data.notes,
        status=RecordStatus.ACTIVE,
    )
    session.add(row)
    session.flush()
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        action="property.create",
        resource_type="property",
        resource_id=row.id,
        summary=f"Created property {row.name}",
    )
    return row


def get_property(session: Session, ctx: OrganisationContext, property_id: uuid.UUID) -> Property:
    row = require_property_for_org(session, ctx, property_id)
    _assert_landlord_scope(ctx, row)
    return row


def list_properties(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    status_filter: RecordStatus | None = None,
) -> tuple[list[Property], int]:
    stmt = select(Property).where(Property.organisation_id == ctx.organisation_id)
    if ctx.role == HMoreRole.LANDLORD:
        stmt = stmt.where(
            or_(
                Property.landlord_user_id == ctx.user_id,
                Property.landlord_user_id.is_(None),
            )
        )
    if status_filter is not None:
        stmt = stmt.where(Property.status == status_filter)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Property.name.ilike(pattern),
                Property.postcode.ilike(pattern),
                Property.city.ilike(pattern),
                Property.address_line1.ilike(pattern),
            )
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(stmt.order_by(Property.created_at.desc()).offset(offset).limit(limit))
    )
    return rows, total


def update_property(
    session: Session,
    ctx: OrganisationContext,
    property_id: uuid.UUID,
    data: PropertyUpdate,
) -> Property:
    row = require_property_for_org(session, ctx, property_id)
    _assert_landlord_scope(ctx, row)
    payload = data.model_dump(exclude_unset=True)
    if ctx.role == HMoreRole.LANDLORD and "landlord_user_id" in payload:
        payload["landlord_user_id"] = ctx.user_id
    if "name" in payload and payload["name"] is not None:
        payload["name"] = payload["name"].strip()
    if "country_code" in payload and payload["country_code"] is not None:
        payload["country_code"] = payload["country_code"].upper()
    for key, value in payload.items():
        setattr(row, key, value)
    session.add(row)
    session.flush()
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        action="property.update",
        resource_type="property",
        resource_id=row.id,
        summary=f"Updated property {row.name}",
    )
    return row


def archive_property(
    session: Session, ctx: OrganisationContext, property_id: uuid.UUID
) -> Property:
    row = require_property_for_org(session, ctx, property_id)
    _assert_landlord_scope(ctx, row)
    row.status = RecordStatus.ARCHIVED
    session.add(row)
    session.flush()
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        action="property.archive",
        resource_type="property",
        resource_id=row.id,
        summary=f"Archived property {row.name}",
    )
    return row


def count_active_rooms(session: Session, property_id: uuid.UUID) -> int:
    return (
        session.scalar(
            select(func.count()).where(
                Room.property_id == property_id,
                Room.status == RecordStatus.ACTIVE,
            )
        )
        or 0
    )
