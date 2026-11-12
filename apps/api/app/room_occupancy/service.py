"""Room occupancy dashboard, count ingest, corrections, history, retention."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.room_occupancy import (
    OccupancyCountingDevice,
    RoomOccupancyAlert,
    RoomOccupancyCountHistory,
    RoomOccupancyManualCorrection,
    RoomOccupancyState,
)
from app.room_occupancy import access, alerts as alerts_mod, gate as gate_mod
from app.room_occupancy.status import compute_occupancy_status
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def state_to_dict(
    state: RoomOccupancyState,
    *,
    property_name: str | None = None,
    room_label: str | None = None,
    floor_label: str | None = None,
    organisation_name: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(state.id),
        "organisation_id": str(state.organisation_id),
        "organisation_name": organisation_name,
        "property_id": str(state.property_id),
        "property_name": property_name,
        "building": property_name,  # no separate building entity — property name used as building label
        "floor": floor_label,
        "room_id": str(state.room_id),
        "room_label": room_label,
        "estimated_count": state.estimated_count if state.occupancy_status != "offline" else None,
        "estimated_count_label": (
            "Estimated people count"
            if state.occupancy_status != "offline" and state.estimated_count is not None
            else "Unavailable (offline)"
        ),
        "max_capacity": state.max_capacity,
        "occupancy_percent": state.occupancy_percent if state.occupancy_status != "offline" else None,
        "occupancy_status": state.occupancy_status,
        "is_manual_correction": state.is_manual_correction,
        "device_id": str(state.device_id) if state.device_id else None,
        "device_connection_status": state.device_connection_status,
        "last_updated_at": state.last_count_at.isoformat() if state.last_count_at else None,
        "source": state.source,
        "availability_status": state.occupancy_status,
    }


def _get_settings(session: Session, ctx: OrganisationContext):
    return gate_mod.get_or_create_settings(session, ctx)


def settings_to_dict(row) -> dict[str, Any]:
    return {
        "near_capacity_percent": row.near_capacity_percent,
        "offline_after_seconds": row.offline_after_seconds,
        "history_retention_days": row.history_retention_days,
        "alert_retention_days": row.alert_retention_days,
    }


def update_settings(
    session: Session,
    ctx: OrganisationContext,
    *,
    near_capacity_percent: int | None = None,
    offline_after_seconds: int | None = None,
    history_retention_days: int | None = None,
    alert_retention_days: int | None = None,
) -> dict[str, Any]:
    access.require_occupancy_settings(ctx)
    row = _get_settings(session, ctx)
    if near_capacity_percent is not None:
        if not 50 <= near_capacity_percent <= 99:
            raise HTTPException(status_code=400, detail="near_capacity_percent must be 50–99")
        row.near_capacity_percent = near_capacity_percent
    if offline_after_seconds is not None:
        if not 30 <= offline_after_seconds <= 86400:
            raise HTTPException(status_code=400, detail="offline_after_seconds out of range")
        row.offline_after_seconds = offline_after_seconds
    if history_retention_days is not None:
        if not 7 <= history_retention_days <= 3650:
            raise HTTPException(status_code=400, detail="history_retention_days out of range")
        row.history_retention_days = history_retention_days
    if alert_retention_days is not None:
        if not 30 <= alert_retention_days <= 3650:
            raise HTTPException(status_code=400, detail="alert_retention_days out of range")
        row.alert_retention_days = alert_retention_days
    session.flush()
    record_event(
        session,
        action=audit_events.ROOM_OCCUPANCY_SETTINGS_UPDATE,
        resource_type="room_occupancy_settings",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Updated room occupancy settings",
        raise_on_error=False,
    )
    return settings_to_dict(row)


def _ensure_state(session: Session, ctx: OrganisationContext, room: Room) -> RoomOccupancyState:
    state = session.scalar(
        select(RoomOccupancyState).where(
            RoomOccupancyState.organisation_id == ctx.organisation_id,
            RoomOccupancyState.room_id == room.id,
        )
    )
    if state is not None:
        return state
    state = RoomOccupancyState(
        organisation_id=ctx.organisation_id,
        property_id=room.property_id,
        room_id=room.id,
        max_capacity=max(1, int(room.max_occupancy or 1)),
        occupancy_status="offline",
        device_connection_status="offline",
        source="none",
    )
    session.add(state)
    session.flush()
    return state


def ingest_count(
    session: Session,
    ctx: OrganisationContext,
    *,
    device_id: uuid.UUID,
    estimated_count: int,
    recorded_at: datetime | None = None,
) -> dict[str, Any]:
    """Ingest edge people-count only. Blocked unless privacy gate allows live counting."""
    access.require_occupancy_settings(ctx)
    gate_mod.assert_live_counting_allowed(session, ctx.organisation_id)

    if estimated_count < 0 or estimated_count > 500:
        raise HTTPException(status_code=400, detail="Invalid estimated_count")

    device = session.get(OccupancyCountingDevice, device_id)
    if device is None or device.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Device not found")
    if not device.is_enabled:
        raise HTTPException(status_code=400, detail="Device is disabled")
    if not device.supports_people_counting or not device.compatibility_verified:
        raise HTTPException(status_code=400, detail="Device is not verified for people counting")
    if not device.stream_activation_allowed:
        raise HTTPException(status_code=403, detail="Stream/count activation is not allowed for this device")
    if device.room_id is None:
        raise HTTPException(status_code=400, detail="Device is not assigned to a room")

    room = session.get(Room, device.room_id)
    if room is None or room.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Room not found")

    settings = _get_settings(session, ctx)
    when = recorded_at or _now()
    device.connection_status = "online"
    device.last_communication_at = when
    device.last_error = None

    state = _ensure_state(session, ctx, room)
    state.max_capacity = max(1, int(room.max_occupancy or state.max_capacity or 1))
    status, percent = compute_occupancy_status(
        estimated_count=estimated_count,
        max_capacity=state.max_capacity,
        near_capacity_percent=settings.near_capacity_percent,
        last_count_at=when,
        offline_after_seconds=settings.offline_after_seconds,
        device_online=True,
        now=when,
    )
    state.estimated_count = estimated_count
    state.occupancy_percent = percent
    state.occupancy_status = status
    state.is_manual_correction = False
    state.device_id = device.id
    state.device_connection_status = "online"
    state.last_count_at = when
    state.source = "edge"
    session.add(
        RoomOccupancyCountHistory(
            organisation_id=ctx.organisation_id,
            property_id=room.property_id,
            room_id=room.id,
            device_id=device.id,
            estimated_count=estimated_count,
            max_capacity=state.max_capacity,
            occupancy_status=status,
            source="edge",
            is_manual_correction=False,
            recorded_at=when,
        )
    )
    session.flush()
    alerts_mod.evaluate_status_alerts(
        session,
        organisation_id=ctx.organisation_id,
        property_id=room.property_id,
        room_id=room.id,
        device_id=device.id,
        occupancy_status=status,
        estimated_count=estimated_count,
        max_capacity=state.max_capacity,
    )
    record_event(
        session,
        action=audit_events.ROOM_OCCUPANCY_COUNT_INGEST,
        resource_type="room_occupancy_state",
        resource_id=state.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Ingested estimated count {estimated_count} for room {room.label}",
        metadata={"status": status, "device_id": str(device.id)},
        raise_on_error=False,
    )
    prop = session.get(Property, room.property_id)
    return state_to_dict(
        state,
        property_name=prop.name if prop else None,
        room_label=room.label,
        floor_label=room.floor_label,
    )


def correct_count(
    session: Session,
    ctx: OrganisationContext,
    room_id: uuid.UUID,
    *,
    corrected_count: int,
    reason: str,
) -> dict[str, Any]:
    access.require_occupancy_correct(ctx)
    if corrected_count < 0 or corrected_count > 500:
        raise HTTPException(status_code=400, detail="Invalid corrected_count")
    if not reason or not reason.strip():
        raise HTTPException(status_code=400, detail="Correction reason is required")

    room = session.get(Room, room_id)
    if room is None or room.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Room not found")

    settings = _get_settings(session, ctx)
    state = _ensure_state(session, ctx, room)
    previous = state.estimated_count
    when = _now()
    state.max_capacity = max(1, int(room.max_occupancy or state.max_capacity or 1))
    # Manual correction assumes device path is known; still compute status from count
    device_online = state.device_connection_status == "online" or state.source in {"edge", "manual"}
    status, percent = compute_occupancy_status(
        estimated_count=corrected_count,
        max_capacity=state.max_capacity,
        near_capacity_percent=settings.near_capacity_percent,
        last_count_at=when,
        offline_after_seconds=settings.offline_after_seconds,
        device_online=True if previous is not None or device_online else True,
        now=when,
    )
    correction = RoomOccupancyManualCorrection(
        organisation_id=ctx.organisation_id,
        property_id=room.property_id,
        room_id=room.id,
        previous_estimated_count=previous,
        corrected_count=corrected_count,
        reason=reason.strip()[:2000],
        corrected_by_user_id=ctx.user_id,
    )
    session.add(correction)
    state.estimated_count = corrected_count
    state.occupancy_percent = percent
    state.occupancy_status = status
    state.is_manual_correction = True
    state.last_count_at = when
    state.source = "manual"
    state.device_connection_status = "online"
    session.add(
        RoomOccupancyCountHistory(
            organisation_id=ctx.organisation_id,
            property_id=room.property_id,
            room_id=room.id,
            device_id=state.device_id,
            estimated_count=corrected_count,
            max_capacity=state.max_capacity,
            occupancy_status=status,
            source="manual",
            is_manual_correction=True,
            recorded_at=when,
        )
    )
    session.flush()
    alerts_mod.evaluate_status_alerts(
        session,
        organisation_id=ctx.organisation_id,
        property_id=room.property_id,
        room_id=room.id,
        device_id=state.device_id,
        occupancy_status=status,
        estimated_count=corrected_count,
        max_capacity=state.max_capacity,
    )
    record_event(
        session,
        action=audit_events.ROOM_OCCUPANCY_COUNT_CORRECT,
        resource_type="room_occupancy_manual_correction",
        resource_id=correction.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Manual occupancy correction for room {room.label}",
        metadata={"previous": previous, "corrected": corrected_count},
        raise_on_error=False,
    )
    prop = session.get(Property, room.property_id)
    return {
        "correction": {
            "id": str(correction.id),
            "previous_estimated_count": previous,
            "corrected_count": corrected_count,
            "reason": correction.reason,
            "corrected_by_user_id": str(ctx.user_id),
            "created_at": correction.created_at.isoformat() if correction.created_at else when.isoformat(),
        },
        "state": state_to_dict(
            state,
            property_name=prop.name if prop else None,
            room_label=room.label,
            floor_label=room.floor_label,
        ),
    }


def list_room_states(
    session: Session,
    ctx: OrganisationContext,
    *,
    property_id: uuid.UUID | None = None,
    floor: str | None = None,
    room_id: uuid.UUID | None = None,
    occupancy_status: str | None = None,
) -> list[dict[str, Any]]:
    access.deny_tenant_and_unauthorised_landlord(ctx)
    record_event(
        session,
        action=audit_events.ROOM_OCCUPANCY_VIEW,
        resource_type="room_occupancy_dashboard",
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Viewed room occupancy dashboard",
        raise_on_error=False,
    )
    stmt = (
        select(RoomOccupancyState, Room, Property)
        .join(Room, Room.id == RoomOccupancyState.room_id)
        .join(Property, Property.id == RoomOccupancyState.property_id)
        .where(RoomOccupancyState.organisation_id == ctx.organisation_id)
    )
    if property_id:
        stmt = stmt.where(RoomOccupancyState.property_id == property_id)
    if room_id:
        stmt = stmt.where(RoomOccupancyState.room_id == room_id)
    if occupancy_status:
        stmt = stmt.where(RoomOccupancyState.occupancy_status == occupancy_status)
    if floor:
        stmt = stmt.where(Room.floor_label == floor)
    rows = session.execute(stmt.order_by(Property.name, Room.label)).all()
    return [
        state_to_dict(state, property_name=prop.name, room_label=room.label, floor_label=room.floor_label)
        for state, room, prop in rows
    ]


def history_summary(
    session: Session,
    ctx: OrganisationContext,
    *,
    room_id: uuid.UUID | None = None,
    period: str = "daily",
    limit: int = 30,
) -> dict[str, Any]:
    access.require_occupancy_read(ctx)
    stmt = select(RoomOccupancyCountHistory).where(
        RoomOccupancyCountHistory.organisation_id == ctx.organisation_id
    )
    if room_id:
        stmt = stmt.where(RoomOccupancyCountHistory.room_id == room_id)
    rows = session.scalars(stmt.order_by(RoomOccupancyCountHistory.recorded_at.desc()).limit(500)).all()

    buckets: dict[str, list[int]] = {}
    for row in rows:
        if period == "monthly":
            key = row.recorded_at.strftime("%Y-%m")
        elif period == "weekly":
            key = f"{row.recorded_at.isocalendar().year}-W{row.recorded_at.isocalendar().week:02d}"
        else:
            key = row.recorded_at.strftime("%Y-%m-%d")
        buckets.setdefault(key, []).append(row.estimated_count)

    summaries = []
    for key, counts in sorted(buckets.items(), reverse=True)[:limit]:
        summaries.append(
            {
                "period": key,
                "samples": len(counts),
                "peak": max(counts) if counts else 0,
                "average": round(sum(counts) / len(counts), 2) if counts else 0,
            }
        )
    peak_overall = max((r.estimated_count for r in rows), default=0)
    return {
        "period": period,
        "summaries": summaries,
        "peak_occupancy": peak_overall,
        "sample_count": len(rows),
        "note": "Count records only — no video, facial or identity data is stored.",
    }


def list_history(
    session: Session,
    ctx: OrganisationContext,
    *,
    room_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    access.require_occupancy_read(ctx)
    stmt = select(RoomOccupancyCountHistory).where(
        RoomOccupancyCountHistory.organisation_id == ctx.organisation_id
    )
    if room_id:
        stmt = stmt.where(RoomOccupancyCountHistory.room_id == room_id)
    rows = session.scalars(stmt.order_by(RoomOccupancyCountHistory.recorded_at.desc()).limit(limit)).all()
    return [
        {
            "id": str(r.id),
            "property_id": str(r.property_id),
            "room_id": str(r.room_id),
            "estimated_count": r.estimated_count,
            "max_capacity": r.max_capacity,
            "occupancy_status": r.occupancy_status,
            "source": r.source,
            "is_manual_correction": r.is_manual_correction,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in rows
    ]


def list_corrections(session: Session, ctx: OrganisationContext, limit: int = 50) -> list[dict[str, Any]]:
    access.require_occupancy_read(ctx)
    rows = session.scalars(
        select(RoomOccupancyManualCorrection)
        .where(RoomOccupancyManualCorrection.organisation_id == ctx.organisation_id)
        .order_by(RoomOccupancyManualCorrection.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "room_id": str(r.room_id),
            "previous_estimated_count": r.previous_estimated_count,
            "corrected_count": r.corrected_count,
            "reason": r.reason,
            "corrected_by_user_id": str(r.corrected_by_user_id),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    access.deny_tenant_and_unauthorised_landlord(ctx)
    gate = gate_mod.get_gate(session, ctx)
    settings = settings_to_dict(_get_settings(session, ctx))
    states = list_room_states(session, ctx)
    by_status: dict[str, int] = {}
    for s in states:
        by_status[s["occupancy_status"]] = by_status.get(s["occupancy_status"], 0) + 1
    return {
        "generated_at": _now().isoformat(),
        "approval_gate": gate,
        "settings": settings,
        "live_counting_active": bool(gate.get("live_counting_enabled")),
        "room_count": len(states),
        "status_counts": by_status,
        "rooms": states[:100],
        "recent_alerts": alerts_mod.list_alerts(session, ctx, status="active", limit=10),
        "privacy_notice": (
            "Estimated people counts only. No facial recognition, identity tracking, "
            "or raw video storage by default. Live camera activation requires a completed approval gate."
        ),
    }


def mark_stale_offline(session: Session) -> dict[str, Any]:
    """Celery sweep: rooms with stale last_count become offline (not zero)."""
    from app.db.models.room_occupancy import RoomOccupancySettings

    now = _now()
    settings_by_org: dict[uuid.UUID, RoomOccupancySettings] = {}
    updated = 0
    for state in session.scalars(select(RoomOccupancyState)).all():
        settings = settings_by_org.get(state.organisation_id)
        if settings is None:
            settings = session.scalar(
                select(RoomOccupancySettings).where(
                    RoomOccupancySettings.organisation_id == state.organisation_id
                )
            )
            if settings is None:
                continue
            settings_by_org[state.organisation_id] = settings
        status, percent = compute_occupancy_status(
            estimated_count=state.estimated_count,
            max_capacity=state.max_capacity,
            near_capacity_percent=settings.near_capacity_percent,
            last_count_at=state.last_count_at,
            offline_after_seconds=settings.offline_after_seconds,
            device_online=state.device_connection_status == "online",
            now=now,
        )
        if status == "offline" and state.occupancy_status != "offline":
            state.occupancy_status = "offline"
            state.occupancy_percent = None
            # Do not zero estimated_count for display — dict layer hides it when offline
            state.device_connection_status = "offline"
            updated += 1
            alerts_mod.evaluate_status_alerts(
                session,
                organisation_id=state.organisation_id,
                property_id=state.property_id,
                room_id=state.room_id,
                device_id=state.device_id,
                occupancy_status="offline",
                estimated_count=None,
                max_capacity=state.max_capacity,
            )
        elif status != state.occupancy_status:
            state.occupancy_status = status
            state.occupancy_percent = percent
            updated += 1
    session.flush()
    return {"updated": updated}


def apply_retention(session: Session) -> dict[str, Any]:
    """Delete history/alerts past org retention windows."""
    from app.db.models.room_occupancy import RoomOccupancySettings

    now = _now()
    deleted_history = 0
    deleted_alerts = 0
    for settings in session.scalars(select(RoomOccupancySettings)).all():
        hist_cut = now - timedelta(days=settings.history_retention_days)
        alert_cut = now - timedelta(days=settings.alert_retention_days)
        h = session.execute(
            delete(RoomOccupancyCountHistory).where(
                RoomOccupancyCountHistory.organisation_id == settings.organisation_id,
                RoomOccupancyCountHistory.recorded_at < hist_cut,
            )
        )
        deleted_history += h.rowcount or 0
        a = session.execute(
            delete(RoomOccupancyAlert).where(
                RoomOccupancyAlert.organisation_id == settings.organisation_id,
                RoomOccupancyAlert.status == "resolved",
                RoomOccupancyAlert.resolved_at.is_not(None),
                RoomOccupancyAlert.resolved_at < alert_cut,
            )
        )
        deleted_alerts += a.rowcount or 0
    session.flush()
    return {"deleted_history": deleted_history, "deleted_alerts": deleted_alerts}
