from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, RecordStatus
from app.db.models.room import Room
from app.records.audit_hook import record_crud_event
from app.records.pagination import offset_limit
from app.records.property_service import get_property
from app.records.schemas import RoomCreate, RoomUpdate
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import require_room_for_org


def create_room(session: Session, ctx: OrganisationContext, data: RoomCreate) -> Room:
    property_row = get_property(session, ctx, data.property_id)
    if property_row.status != RecordStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add rooms to an archived property",
        )
    if data.max_occupancy is not None and data.max_occupancy < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_occupancy must be a positive integer",
        )
    room = Room(
        organisation_id=ctx.organisation_id,
        property_id=property_row.id,
        label=data.label.strip(),
        floor_label=data.floor_label,
        room_type=data.room_type,
        max_occupancy=data.max_occupancy,
        notes=data.notes,
        status=RecordStatus.ACTIVE,
    )
    session.add(room)
    try:
        session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room label already exists on this property",
        ) from exc
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        action="room.create",
        resource_type="room",
        resource_id=room.id,
        summary=f"Created room {room.label}",
    )
    return room


def get_room(session: Session, ctx: OrganisationContext, room_id: uuid.UUID) -> Room:
    room = require_room_for_org(session, ctx, room_id)
    # Landlord ownership is validated via parent property.
    get_property(session, ctx, room.property_id)
    return room


def list_rooms(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    property_id: uuid.UUID | None = None,
    q: str | None = None,
    status_filter: RecordStatus | None = None,
) -> tuple[list[Room], int]:
    stmt = select(Room).where(Room.organisation_id == ctx.organisation_id)
    if property_id is not None:
        # Ensures landlord scope and org match.
        get_property(session, ctx, property_id)
        stmt = stmt.where(Room.property_id == property_id)
    elif ctx.role == HMoreRole.LANDLORD:
        from app.db.models.property import Property

        owned = select(Property.id).where(
            Property.organisation_id == ctx.organisation_id,
            or_(
                Property.landlord_user_id == ctx.user_id,
                Property.landlord_user_id.is_(None),
            ),
        )
        stmt = stmt.where(Room.property_id.in_(owned))
    if status_filter is not None:
        stmt = stmt.where(Room.status == status_filter)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Room.label.ilike(pattern), Room.room_type.ilike(pattern), Room.floor_label.ilike(pattern))
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(session.scalars(stmt.order_by(Room.created_at.desc()).offset(offset).limit(limit)))
    return rows, total


def update_room(
    session: Session,
    ctx: OrganisationContext,
    room_id: uuid.UUID,
    data: RoomUpdate,
) -> Room:
    room = get_room(session, ctx, room_id)
    payload = data.model_dump(exclude_unset=True)
    if "label" in payload and payload["label"] is not None:
        payload["label"] = payload["label"].strip()
    if "max_occupancy" in payload and payload["max_occupancy"] is not None:
        if payload["max_occupancy"] < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_occupancy must be a positive integer",
            )
    for key, value in payload.items():
        setattr(room, key, value)
    session.add(room)
    try:
        session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room label already exists on this property",
        ) from exc
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        action="room.update",
        resource_type="room",
        resource_id=room.id,
        summary=f"Updated room {room.label}",
    )
    return room


def archive_room(session: Session, ctx: OrganisationContext, room_id: uuid.UUID) -> Room:
    room = get_room(session, ctx, room_id)
    room.status = RecordStatus.ARCHIVED
    session.add(room)
    session.flush()
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        action="room.archive",
        resource_type="room",
        resource_id=room.id,
        summary=f"Archived room {room.label}",
    )
    return room
