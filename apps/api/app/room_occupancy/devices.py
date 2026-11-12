"""Counting device registration — credentials encrypted; streams gated."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.room_occupancy import OccupancyCountingDevice
from app.integrations.crypto import encrypt_credentials, public_credentials_view
from app.room_occupancy import access, gate as gate_mod
from app.room_occupancy.constants import DEVICE_TYPES, FORBIDDEN_ROOM_TYPE_KEYWORDS
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _room_type_forbidden(room_type: str | None) -> bool:
    if not room_type:
        return False
    token = room_type.strip().lower().replace(" ", "_")
    if token in FORBIDDEN_ROOM_TYPE_KEYWORDS:
        return True
    return any(k in token for k in FORBIDDEN_ROOM_TYPE_KEYWORDS)


def device_to_dict(row: OccupancyCountingDevice) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "device_key": row.device_key,
        "name": row.name,
        "device_type": row.device_type,
        "property_id": str(row.property_id),
        "room_id": str(row.room_id) if row.room_id else None,
        "supports_people_counting": row.supports_people_counting,
        "compatibility_verified": row.compatibility_verified,
        "stream_activation_allowed": row.stream_activation_allowed,
        "connection_status": row.connection_status,
        "last_communication_at": row.last_communication_at.isoformat() if row.last_communication_at else None,
        "last_error": row.last_error,
        "config": {k: v for k, v in (row.config_json or {}).items() if k not in {"rtsp_url", "password"}},
        "credentials": public_credentials_view(row.credentials_meta),
        "is_enabled": row.is_enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def register_device(
    session: Session,
    ctx: OrganisationContext,
    *,
    device_key: str,
    name: str,
    device_type: str,
    property_id: uuid.UUID,
    room_id: uuid.UUID | None = None,
    supports_people_counting: bool = False,
    compatibility_verified: bool = False,
    config: dict[str, Any] | None = None,
    credentials: dict[str, Any] | None = None,
) -> dict[str, Any]:
    access.require_occupancy_settings(ctx)
    if device_type not in DEVICE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid device_type")
    prop = session.get(Property, property_id)
    if prop is None or prop.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Property not found")
    if room_id is not None:
        room = session.get(Room, room_id)
        if room is None or room.organisation_id != ctx.organisation_id or room.property_id != property_id:
            raise HTTPException(status_code=404, detail="Room not found")
        if _room_type_forbidden(room.room_type):
            raise HTTPException(
                status_code=400,
                detail="Cameras/sensors must not be assigned to bedrooms, bathrooms or changing rooms",
            )

    approval = gate_mod.get_or_create_gate(session, ctx)
    # Never activate RTSP/streams without complete gate + verified counting support
    stream_ok = (
        gate_mod.is_gate_complete(approval)
        and approval.live_counting_enabled
        and supports_people_counting
        and compatibility_verified
    )

    ciphertext, meta = encrypt_credentials(credentials)
    row = OccupancyCountingDevice(
        organisation_id=ctx.organisation_id,
        device_key=device_key.strip()[:64],
        name=name.strip()[:200],
        device_type=device_type,
        property_id=property_id,
        room_id=room_id,
        supports_people_counting=supports_people_counting,
        compatibility_verified=compatibility_verified,
        stream_activation_allowed=stream_ok,
        connection_status="pending",
        config_json=config or {},
        credentials_encrypted=ciphertext,
        credentials_meta=meta,
        is_enabled=True,
        created_by_user_id=ctx.user_id,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Device key already registered") from exc

    record_event(
        session,
        action=audit_events.ROOM_OCCUPANCY_DEVICE_REGISTER,
        resource_type="occupancy_counting_device",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Registered occupancy device {row.name}",
        metadata={
            "device_type": device_type,
            "stream_activation_allowed": stream_ok,
            "compatibility_verified": compatibility_verified,
        },
        raise_on_error=False,
    )
    return device_to_dict(row)


def list_devices(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    access.require_occupancy_read(ctx)
    rows = session.scalars(
        select(OccupancyCountingDevice)
        .where(OccupancyCountingDevice.organisation_id == ctx.organisation_id)
        .order_by(OccupancyCountingDevice.created_at.desc())
    ).all()
    return [device_to_dict(r) for r in rows]


def update_device(
    session: Session,
    ctx: OrganisationContext,
    device_id: uuid.UUID,
    *,
    name: str | None = None,
    room_id: uuid.UUID | None = None,
    clear_room: bool = False,
    supports_people_counting: bool | None = None,
    compatibility_verified: bool | None = None,
    is_enabled: bool | None = None,
    connection_status: str | None = None,
    last_error: str | None = None,
    config: dict[str, Any] | None = None,
    credentials: dict[str, Any] | None = None,
) -> dict[str, Any]:
    access.require_occupancy_settings(ctx)
    row = session.get(OccupancyCountingDevice, device_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Device not found")
    if name is not None:
        row.name = name.strip()[:200]
    if clear_room:
        row.room_id = None
    elif room_id is not None:
        room = session.get(Room, room_id)
        if room is None or room.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=404, detail="Room not found")
        if _room_type_forbidden(room.room_type):
            raise HTTPException(
                status_code=400,
                detail="Cameras/sensors must not be assigned to bedrooms, bathrooms or changing rooms",
            )
        row.room_id = room_id
        row.property_id = room.property_id
    if supports_people_counting is not None:
        row.supports_people_counting = supports_people_counting
    if compatibility_verified is not None:
        row.compatibility_verified = compatibility_verified
    if is_enabled is not None:
        row.is_enabled = is_enabled
        if not is_enabled:
            row.connection_status = "disabled"
            row.stream_activation_allowed = False
    if connection_status is not None:
        row.connection_status = connection_status
        row.last_communication_at = _now()
    if last_error is not None:
        row.last_error = last_error[:2000]
    if config is not None:
        row.config_json = config
    if credentials is not None:
        ciphertext, meta = encrypt_credentials(credentials)
        if ciphertext:
            row.credentials_encrypted = ciphertext
            row.credentials_meta = meta

    approval = gate_mod.get_or_create_gate(session, ctx)
    row.stream_activation_allowed = bool(
        gate_mod.is_gate_complete(approval)
        and approval.live_counting_enabled
        and row.supports_people_counting
        and row.compatibility_verified
        and row.is_enabled
    )
    session.flush()
    return device_to_dict(row)
