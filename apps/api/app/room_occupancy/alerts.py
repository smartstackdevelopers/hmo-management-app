"""Capacity and offline alerts with active-condition dedupe."""

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
from app.db.models.room_occupancy import RoomOccupancyAlert
from app.room_occupancy import access
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def alert_to_dict(row: RoomOccupancyAlert) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "property_id": str(row.property_id),
        "room_id": str(row.room_id),
        "device_id": str(row.device_id) if row.device_id else None,
        "alert_category": row.alert_category,
        "severity": row.severity,
        "estimated_count": row.estimated_count,
        "max_capacity": row.max_capacity,
        "status": row.status,
        "message": row.message,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }


def raise_or_refresh_alert(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    property_id: uuid.UUID,
    room_id: uuid.UUID,
    device_id: uuid.UUID | None,
    category: str,
    severity: str,
    message: str,
    estimated_count: int | None,
    max_capacity: int | None,
) -> RoomOccupancyAlert | None:
    existing = session.scalar(
        select(RoomOccupancyAlert).where(
            RoomOccupancyAlert.organisation_id == organisation_id,
            RoomOccupancyAlert.room_id == room_id,
            RoomOccupancyAlert.alert_category == category,
            RoomOccupancyAlert.dedupe_key == "active",
            RoomOccupancyAlert.status == "active",
        )
    )
    if existing is not None:
        existing.estimated_count = estimated_count
        existing.max_capacity = max_capacity
        existing.message = message[:2000]
        existing.severity = severity
        session.flush()
        return existing

    row = RoomOccupancyAlert(
        organisation_id=organisation_id,
        property_id=property_id,
        room_id=room_id,
        device_id=device_id,
        alert_category=category,
        severity=severity,
        estimated_count=estimated_count,
        max_capacity=max_capacity,
        status="active",
        dedupe_key="active",
        message=message[:2000],
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError:
        # Concurrent insert for same active dedupe — treat as already raised
        return existing
    record_event(
        session,
        action=audit_events.ROOM_OCCUPANCY_ALERT_RAISE,
        resource_type="room_occupancy_alert",
        resource_id=row.id,
        organisation_id=organisation_id,
        outcome=AuditOutcome.SUCCESS,
        summary=message[:255],
        metadata={"category": category},
        raise_on_error=False,
    )
    return row


def resolve_alert_category(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    room_id: uuid.UUID,
    category: str,
) -> None:
    rows = session.scalars(
        select(RoomOccupancyAlert).where(
            RoomOccupancyAlert.organisation_id == organisation_id,
            RoomOccupancyAlert.room_id == room_id,
            RoomOccupancyAlert.alert_category == category,
            RoomOccupancyAlert.status == "active",
        )
    ).all()
    for row in rows:
        row.status = "resolved"
        row.dedupe_key = f"resolved:{row.id}"
        row.resolved_at = _now()
    session.flush()


def evaluate_status_alerts(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    property_id: uuid.UUID,
    room_id: uuid.UUID,
    device_id: uuid.UUID | None,
    occupancy_status: str,
    estimated_count: int | None,
    max_capacity: int,
) -> None:
    if occupancy_status == "at_capacity":
        raise_or_refresh_alert(
            session,
            organisation_id=organisation_id,
            property_id=property_id,
            room_id=room_id,
            device_id=device_id,
            category="at_capacity",
            severity="critical",
            message="Room has reached maximum capacity",
            estimated_count=estimated_count,
            max_capacity=max_capacity,
        )
    else:
        resolve_alert_category(session, organisation_id=organisation_id, room_id=room_id, category="at_capacity")

    if occupancy_status == "near_capacity":
        raise_or_refresh_alert(
            session,
            organisation_id=organisation_id,
            property_id=property_id,
            room_id=room_id,
            device_id=device_id,
            category="near_capacity",
            severity="warning",
            message="Room is approaching maximum capacity",
            estimated_count=estimated_count,
            max_capacity=max_capacity,
        )
    else:
        resolve_alert_category(session, organisation_id=organisation_id, room_id=room_id, category="near_capacity")

    if occupancy_status == "offline":
        raise_or_refresh_alert(
            session,
            organisation_id=organisation_id,
            property_id=property_id,
            room_id=room_id,
            device_id=device_id,
            category="device_offline",
            severity="warning",
            message="Counting equipment is offline or not providing valid updates",
            estimated_count=None,
            max_capacity=max_capacity,
        )
        raise_or_refresh_alert(
            session,
            organisation_id=organisation_id,
            property_id=property_id,
            room_id=room_id,
            device_id=device_id,
            category="missing_updates",
            severity="warning",
            message="Missing occupancy updates from counting equipment",
            estimated_count=None,
            max_capacity=max_capacity,
        )
    else:
        resolve_alert_category(session, organisation_id=organisation_id, room_id=room_id, category="device_offline")
        resolve_alert_category(session, organisation_id=organisation_id, room_id=room_id, category="missing_updates")


def list_alerts(
    session: Session,
    ctx: OrganisationContext,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    access.require_occupancy_read(ctx)
    stmt = select(RoomOccupancyAlert).where(RoomOccupancyAlert.organisation_id == ctx.organisation_id)
    if status:
        stmt = stmt.where(RoomOccupancyAlert.status == status)
    rows = session.scalars(stmt.order_by(RoomOccupancyAlert.created_at.desc()).limit(limit)).all()
    return [alert_to_dict(r) for r in rows]


def acknowledge_alert(session: Session, ctx: OrganisationContext, alert_id: uuid.UUID) -> dict[str, Any]:
    access.require_occupancy_alerts_manage(ctx)
    row = session.get(RoomOccupancyAlert, alert_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    if row.status == "active":
        row.status = "acknowledged"
        row.dedupe_key = f"acknowledged:{row.id}"
        session.flush()
    return alert_to_dict(row)
