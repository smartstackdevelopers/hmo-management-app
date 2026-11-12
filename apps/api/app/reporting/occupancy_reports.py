"""Occupancy analytics (F6.2) — reuses F6.1 room/tenant occupancy math."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, RecordStatus
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.tenant import Tenant
from app.landlord_enterprise.access import landlord_property_filter
from app.reporting.access import require_occupancy_reports
from app.reporting.filters import OccupancyReportFilters
from app.records.pagination import offset_limit
from app.tenancy.context import OrganisationContext


def _property_ids(session: Session, ctx: OrganisationContext, flt: OccupancyReportFilters) -> list[uuid.UUID]:
    stmt = select(Property).where(
        Property.organisation_id == ctx.organisation_id,
        Property.status == RecordStatus.ACTIVE,
        landlord_property_filter(ctx),
    )
    if flt.property_id:
        stmt = stmt.where(Property.id == flt.property_id)
    props = list(session.scalars(stmt).all())
    if flt.building:
        needle = flt.building.strip().lower()
        props = [
            p
            for p in props
            if needle in p.name.lower()
            or needle in (p.city or "").lower()
            or needle in (p.address_line1 or "").lower()
        ]
    return [p.id for p in props]


def _occupancy_for_property(
    session: Session, ctx: OrganisationContext, prop: Property
) -> dict[str, Any]:
    rooms = list(
        session.scalars(
            select(Room).where(
                Room.organisation_id == ctx.organisation_id,
                Room.property_id == prop.id,
                Room.status == RecordStatus.ACTIVE,
            )
        ).all()
    )
    tenants = list(
        session.scalars(
            select(Tenant).where(
                Tenant.organisation_id == ctx.organisation_id,
                Tenant.assigned_property_id == prop.id,
                Tenant.status == RecordStatus.ACTIVE,
            )
        ).all()
    )
    occupied_room_ids = {t.assigned_room_id for t in tenants if t.assigned_room_id}
    occupied = sum(1 for r in rooms if r.id in occupied_room_ids)
    vacant = max(0, len(rooms) - occupied)
    capacity = sum(r.max_occupancy or 1 for r in rooms)
    room_rows = [
        {
            "room_id": str(r.id),
            "label": r.label,
            "floor_label": r.floor_label,
            "max_occupancy": r.max_occupancy,
            "status": "occupied" if r.id in occupied_room_ids else "vacant",
        }
        for r in rooms
    ]
    return {
        "property_id": str(prop.id),
        "property_name": prop.name,
        "building": prop.name,
        "city": prop.city,
        "postcode": prop.postcode,
        "total_rooms": len(rooms),
        "occupied_rooms": occupied,
        "vacant_rooms": vacant,
        "occupancy_rate": round((occupied / len(rooms)) * 100, 1) if rooms else 0.0,
        "capacity": capacity,
        "active_tenancies": len(tenants),
        "rooms": room_rows,
    }


def occupancy_summary(session: Session, ctx: OrganisationContext, flt: OccupancyReportFilters) -> dict[str, Any]:
    require_occupancy_reports(ctx)
    flt.validate_window()
    ids = _property_ids(session, ctx, flt)
    if not ids:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_properties": 0,
            "total_rooms": 0,
            "occupied_rooms": 0,
            "vacant_rooms": 0,
            "occupancy_rate": 0.0,
            "capacity": 0,
            "by_property": [],
            "trend_comparison": [],
            "definitions": {
                "occupancy": "Active rooms with an assigned active tenant (same as F6.1 landlord dashboard)",
            },
        }
    props = list(
        session.scalars(
            select(Property).where(
                Property.organisation_id == ctx.organisation_id,
                Property.id.in_(ids),
            )
        ).all()
    )
    by_property = [_occupancy_for_property(session, ctx, p) for p in props]
    total_rooms = sum(p["total_rooms"] for p in by_property)
    occupied = sum(p["occupied_rooms"] for p in by_property)
    vacant = sum(p["vacant_rooms"] for p in by_property)
    capacity = sum(p["capacity"] for p in by_property)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_properties": len(by_property),
        "total_rooms": total_rooms,
        "occupied_rooms": occupied,
        "vacant_rooms": vacant,
        "occupancy_rate": round((occupied / total_rooms) * 100, 1) if total_rooms else 0.0,
        "capacity": capacity,
        "by_property": [
            {
                "property_id": p["property_id"],
                "property_name": p["property_name"],
                "occupied_rooms": p["occupied_rooms"],
                "vacant_rooms": p["vacant_rooms"],
                "occupancy_rate": p["occupancy_rate"],
                "capacity": p["capacity"],
            }
            for p in by_property
        ],
        "trend_comparison": [
            {
                "label": p["property_name"],
                "occupied": p["occupied_rooms"],
                "vacant": p["vacant_rooms"],
            }
            for p in by_property
        ],
        "definitions": {
            "occupancy": "Active rooms with an assigned active tenant (same as F6.1 landlord dashboard)",
            "capacity": "Sum of room max_occupancy (defaults to 1 when unset)",
        },
    }


def occupancy_rows(
    session: Session, ctx: OrganisationContext, flt: OccupancyReportFilters
) -> tuple[list[dict[str, Any]], int]:
    require_occupancy_reports(ctx)
    flt.validate_window()
    ids = _property_ids(session, ctx, flt)
    props = list(
        session.scalars(
            select(Property).where(
                Property.organisation_id == ctx.organisation_id,
                Property.id.in_(ids) if ids else False,
            )
        ).all()
    )
    rows: list[dict[str, Any]] = []
    for prop in props:
        block = _occupancy_for_property(session, ctx, prop)
        for room in block["rooms"]:
            rows.append(
                {
                    "property_id": block["property_id"],
                    "property_name": block["property_name"],
                    "building": block["building"],
                    "room_id": room["room_id"],
                    "room_label": room["label"],
                    "floor_label": room["floor_label"],
                    "max_occupancy": room["max_occupancy"],
                    "status": room["status"],
                    "property_occupancy_rate": block["occupancy_rate"],
                }
            )
    total = len(rows)
    offset, limit = offset_limit(flt.page, flt.page_size)
    return rows[offset : offset + limit], total
