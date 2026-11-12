"""F6.1 landlord enterprise services — real aggregates over owned properties."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.enums import RecordStatus
from app.db.models.landlord_enterprise import PropertyInspection, RentRecord
from app.db.models.maintenance import MaintenanceRequest
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.tenant import Tenant
from app.landlord_enterprise import access
from app.landlord_enterprise.constants import (
    COMPLETED_REPAIR_STATUSES,
    INSPECTION_STATUSES,
    LEDGER_DISCLAIMER,
    OPEN_REPAIR_STATUSES,
    RENT_STATUSES,
)
from app.landlord_enterprise.schemas import (
    InspectionWrite,
    RentRecordStatusWrite,
    RentRecordWrite,
)
from app.tenancy.context import OrganisationContext


def _audit(
    session: Session,
    ctx: OrganisationContext,
    *,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    summary: str,
) -> None:
    record_event(
        session,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary=summary,
        raise_on_error=False,
    )


def _property_ids(session: Session, ctx: OrganisationContext, property_id: uuid.UUID | None = None) -> list[uuid.UUID]:
    ids = access.list_accessible_property_ids(session, ctx)
    if property_id is not None:
        if property_id not in ids:
            access.get_accessible_property(session, ctx, property_id)
        return [property_id]
    return ids


def _effective_inspection_status(row: PropertyInspection, today: date | None = None) -> str:
    today = today or date.today()
    if row.status in {"completed", "cancelled"}:
        return row.status
    if row.scheduled_date < today and row.status in {"scheduled", "in_progress"}:
        return "overdue"
    return row.status


def enterprise_dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    access.require_landlord_enterprise_read(ctx)
    property_ids = access.list_accessible_property_ids(session, ctx)
    today = date.today()

    total_properties = len(property_ids)
    if not property_ids:
        return {
            "total_properties": 0,
            "total_rooms": 0,
            "occupied_rooms": 0,
            "vacant_rooms": 0,
            "active_tenancies": 0,
            "rent": {"due": 0, "outstanding": 0, "recorded_paid": 0, "total": 0},
            "inspections": {"upcoming": 0, "overdue": 0, "completed": 0},
            "repairs": {"open": 0, "completed": 0, "pending_maintenance": 0},
            "ledger_disclaimer": LEDGER_DISCLAIMER,
            "properties": [],
        }

    rooms = list(
        session.scalars(
            select(Room).where(
                Room.organisation_id == ctx.organisation_id,
                Room.property_id.in_(property_ids),
                Room.status == RecordStatus.ACTIVE,
            )
        ).all()
    )
    occupied_room_ids = set(
        session.scalars(
            select(Tenant.assigned_room_id).where(
                Tenant.organisation_id == ctx.organisation_id,
                Tenant.status == RecordStatus.ACTIVE,
                Tenant.assigned_property_id.in_(property_ids),
                Tenant.assigned_room_id.is_not(None),
            )
        ).all()
    )
    occupied_rooms = sum(1 for room in rooms if room.id in occupied_room_ids)
    vacant_rooms = max(0, len(rooms) - occupied_rooms)
    active_tenancies = session.scalar(
        select(func.count()).select_from(Tenant).where(
            Tenant.organisation_id == ctx.organisation_id,
            Tenant.status == RecordStatus.ACTIVE,
            Tenant.assigned_property_id.in_(property_ids),
        )
    ) or 0

    rent_rows = list(
        session.scalars(
            select(RentRecord).where(
                RentRecord.organisation_id == ctx.organisation_id,
                RentRecord.property_id.in_(property_ids),
                RentRecord.is_archived.is_(False),
            )
        ).all()
    )
    rent_counts = {status: 0 for status in RENT_STATUSES}
    for row in rent_rows:
        rent_counts[row.status] = rent_counts.get(row.status, 0) + 1

    inspections = list(
        session.scalars(
            select(PropertyInspection).where(
                PropertyInspection.organisation_id == ctx.organisation_id,
                PropertyInspection.property_id.in_(property_ids),
                PropertyInspection.is_archived.is_(False),
            )
        ).all()
    )
    upcoming = sum(
        1
        for row in inspections
        if _effective_inspection_status(row, today) == "scheduled" and row.scheduled_date >= today
    )
    overdue = sum(1 for row in inspections if _effective_inspection_status(row, today) == "overdue")
    completed_insp = sum(1 for row in inspections if row.status == "completed")

    repairs = list(
        session.scalars(
            select(MaintenanceRequest).where(
                MaintenanceRequest.organisation_id == ctx.organisation_id,
                MaintenanceRequest.property_id.in_(property_ids),
            )
        ).all()
    )
    open_repairs = sum(1 for row in repairs if row.status in OPEN_REPAIR_STATUSES)
    completed_repairs = sum(1 for row in repairs if row.status in COMPLETED_REPAIR_STATUSES)
    pending_maintenance = sum(
        1 for row in repairs if row.status in {"awaiting_approval", "awaiting_parts", "on_hold", "approved"}
    )

    props = list(
        session.scalars(
            select(Property).where(
                Property.organisation_id == ctx.organisation_id,
                Property.id.in_(property_ids),
            )
        ).all()
    )

    return {
        "total_properties": total_properties,
        "total_rooms": len(rooms),
        "occupied_rooms": occupied_rooms,
        "vacant_rooms": vacant_rooms,
        "active_tenancies": int(active_tenancies),
        "rent": {
            "due": rent_counts.get("due", 0),
            "outstanding": rent_counts.get("outstanding", 0),
            "recorded_paid": rent_counts.get("recorded_paid", 0),
            "total": len(rent_rows),
        },
        "inspections": {"upcoming": upcoming, "overdue": overdue, "completed": completed_insp},
        "repairs": {
            "open": open_repairs,
            "completed": completed_repairs,
            "pending_maintenance": pending_maintenance,
        },
        "ledger_disclaimer": LEDGER_DISCLAIMER,
        "properties": [
            {
                "id": str(p.id),
                "name": p.name,
                "city": p.city,
                "postcode": p.postcode,
            }
            for p in props
        ],
    }


def portfolio_analytics(
    session: Session,
    ctx: OrganisationContext,
    *,
    property_id: uuid.UUID | None = None,
    building: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    tenancy_status: str | None = None,
    inspection_status: str | None = None,
    repair_status: str | None = None,
) -> dict[str, Any]:
    access.require_landlord_enterprise_read(ctx)
    property_ids = _property_ids(session, ctx, property_id)
    today = date.today()

    props = list(
        session.scalars(
            select(Property).where(
                Property.organisation_id == ctx.organisation_id,
                Property.id.in_(property_ids) if property_ids else False,
            )
        ).all()
    )
    if building:
        needle = building.strip().lower()
        props = [
            p
            for p in props
            if needle in p.name.lower() or needle in p.city.lower() or needle in (p.address_line1 or "").lower()
        ]
        property_ids = [p.id for p in props]

    items: list[dict[str, Any]] = []
    for prop in props:
        rooms = list(
            session.scalars(
                select(Room).where(
                    Room.organisation_id == ctx.organisation_id,
                    Room.property_id == prop.id,
                    Room.status == RecordStatus.ACTIVE,
                )
            ).all()
        )
        tenants_q = select(Tenant).where(
            Tenant.organisation_id == ctx.organisation_id,
            Tenant.assigned_property_id == prop.id,
            Tenant.status == RecordStatus.ACTIVE,
        )
        tenants = list(session.scalars(tenants_q).all())
        if tenancy_status == "occupied" and not tenants:
            continue
        if tenancy_status == "vacant" and tenants:
            continue
        occupied_room_ids = {t.assigned_room_id for t in tenants if t.assigned_room_id}
        occupied = sum(1 for r in rooms if r.id in occupied_room_ids)
        vacant = max(0, len(rooms) - occupied)

        insp = list(
            session.scalars(
                select(PropertyInspection).where(
                    PropertyInspection.organisation_id == ctx.organisation_id,
                    PropertyInspection.property_id == prop.id,
                    PropertyInspection.is_archived.is_(False),
                )
            ).all()
        )
        if date_from:
            insp = [i for i in insp if i.scheduled_date >= date_from]
        if date_to:
            insp = [i for i in insp if i.scheduled_date <= date_to]
        if inspection_status:
            insp = [i for i in insp if _effective_inspection_status(i, today) == inspection_status]

        repairs = list(
            session.scalars(
                select(MaintenanceRequest).where(
                    MaintenanceRequest.organisation_id == ctx.organisation_id,
                    MaintenanceRequest.property_id == prop.id,
                )
            ).all()
        )
        if repair_status:
            repairs = [r for r in repairs if r.status == repair_status]
        open_repairs = sum(1 for r in repairs if r.status in OPEN_REPAIR_STATUSES)

        items.append(
            {
                "property_id": str(prop.id),
                "property_name": prop.name,
                "building": prop.name,
                "city": prop.city,
                "postcode": prop.postcode,
                "total_rooms": len(rooms),
                "occupied_rooms": occupied,
                "vacant_rooms": vacant,
                "occupancy_rate": round((occupied / len(rooms)) * 100, 1) if rooms else 0.0,
                "active_tenancies": len(tenants),
                "tenancy_status": "occupied" if tenants else "vacant",
                "outstanding_repairs": open_repairs,
                "inspection_count": len(insp),
                "last_inspection_date": max((i.scheduled_date for i in insp), default=None),
                "maintenance_status": "attention" if open_repairs else "clear",
            }
        )

    vacancy_trend = [
        {
            "property_id": item["property_id"],
            "property_name": item["property_name"],
            "vacant_rooms": item["vacant_rooms"],
            "occupied_rooms": item["occupied_rooms"],
        }
        for item in items
    ]
    return {"items": items, "vacancy_trend": vacancy_trend, "total": len(items)}


def _rent_out(session: Session, row: RentRecord) -> dict[str, Any]:
    prop = session.get(Property, row.property_id)
    tenant = session.get(Tenant, row.tenant_id) if row.tenant_id else None
    return {
        "id": row.id,
        "property_id": row.property_id,
        "property_name": prop.name if prop else None,
        "room_id": row.room_id,
        "tenant_id": row.tenant_id,
        "tenant_name": (tenant.preferred_name if tenant else None),
        "amount": row.amount,
        "currency": row.currency,
        "period_start": row.period_start,
        "period_end": row.period_end,
        "due_date": row.due_date,
        "status": row.status,
        "tenancy_reference": row.tenancy_reference,
        "notes": row.notes,
        "recorded_paid_at": row.recorded_paid_at,
        "recorded_paid_note": row.recorded_paid_note,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_rent_records(
    session: Session,
    ctx: OrganisationContext,
    *,
    property_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    access.require_rent_manage(ctx)
    property_ids = _property_ids(session, ctx, property_id)
    stmt = select(RentRecord).where(
        RentRecord.organisation_id == ctx.organisation_id,
        RentRecord.is_archived.is_(False),
        RentRecord.property_id.in_(property_ids) if property_ids else False,
    )
    if tenant_id:
        stmt = stmt.where(RentRecord.tenant_id == tenant_id)
    if status:
        if status not in RENT_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid rent status")
        stmt = stmt.where(RentRecord.status == status)
    if date_from:
        stmt = stmt.where(RentRecord.period_start >= date_from)
    if date_to:
        stmt = stmt.where(RentRecord.period_end <= date_to)
    rows = list(session.scalars(stmt.order_by(RentRecord.period_start.desc())).all())
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return {
        "items": [_rent_out(session, row) for row in page_rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "disclaimer": LEDGER_DISCLAIMER,
    }


def get_rent_record(session: Session, ctx: OrganisationContext, rent_id: uuid.UUID) -> dict[str, Any]:
    access.require_rent_manage(ctx)
    row = session.get(RentRecord, rent_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.is_archived:
        raise HTTPException(status_code=404, detail="Rent record not found")
    access.get_accessible_property(session, ctx, row.property_id)
    return _rent_out(session, row)


def create_rent_record(session: Session, ctx: OrganisationContext, data: RentRecordWrite) -> dict[str, Any]:
    access.require_rent_manage(ctx)
    access.get_accessible_property(session, ctx, data.property_id)
    if data.period_end < data.period_start:
        raise HTTPException(status_code=422, detail="period_end must be on or after period_start")
    if data.status not in RENT_STATUSES or data.status == "recorded_paid":
        raise HTTPException(
            status_code=422,
            detail="Create with due/outstanding/waived/cancelled; use status endpoint to record payment",
        )
    if data.room_id:
        access.assert_room_on_property(session, ctx, data.room_id, data.property_id)
    if data.tenant_id:
        tenant = access.assert_tenant_on_property(session, ctx, data.tenant_id, data.property_id)
        tenancy_ref = data.tenancy_reference or tenant.tenancy_reference
    else:
        tenancy_ref = data.tenancy_reference

    row = RentRecord(
        id=uuid.uuid4(),
        organisation_id=ctx.organisation_id,
        property_id=data.property_id,
        room_id=data.room_id,
        tenant_id=data.tenant_id,
        amount=data.amount,
        currency=(data.currency or "GBP").upper(),
        period_start=data.period_start,
        period_end=data.period_end,
        due_date=data.due_date,
        status=data.status,
        tenancy_reference=tenancy_ref,
        notes=data.notes,
    )
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.LANDLORD_RENT_CREATE,
        resource_type="rent_record",
        resource_id=row.id,
        summary="Rent record created",
    )
    return _rent_out(session, row)


def update_rent_status(
    session: Session, ctx: OrganisationContext, rent_id: uuid.UUID, data: RentRecordStatusWrite
) -> dict[str, Any]:
    access.require_rent_manage(ctx)
    row = session.get(RentRecord, rent_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.is_archived:
        raise HTTPException(status_code=404, detail="Rent record not found")
    access.get_accessible_property(session, ctx, row.property_id)
    if data.status not in RENT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid rent status")
    if data.status == "recorded_paid":
        note = (data.recorded_paid_note or "").strip()
        if len(note) < 3:
            raise HTTPException(
                status_code=422,
                detail="recorded_paid_note is required to mark rent as recorded paid (no payment gateway)",
            )
        row.recorded_paid_at = datetime.now(timezone.utc)
        row.recorded_paid_by_user_id = ctx.user_id
        row.recorded_paid_note = note
    elif row.status == "recorded_paid" and data.status != "recorded_paid":
        # Clearing paid status also requires a note for auditability
        note = (data.recorded_paid_note or "").strip()
        if len(note) < 3:
            raise HTTPException(status_code=422, detail="Note required when changing a recorded paid status")
        row.recorded_paid_note = note
    row.status = data.status
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.LANDLORD_RENT_STATUS,
        resource_type="rent_record",
        resource_id=row.id,
        summary=f"Rent status set to {data.status}",
    )
    return _rent_out(session, row)


def archive_rent_record(session: Session, ctx: OrganisationContext, rent_id: uuid.UUID) -> dict[str, str]:
    access.require_rent_manage(ctx)
    row = session.get(RentRecord, rent_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Rent record not found")
    access.get_accessible_property(session, ctx, row.property_id)
    row.is_archived = True
    session.add(row)
    session.flush()
    return {"status": "archived"}


def _inspection_out(session: Session, row: PropertyInspection) -> dict[str, Any]:
    prop = session.get(Property, row.property_id)
    return {
        "id": row.id,
        "property_id": row.property_id,
        "property_name": prop.name if prop else None,
        "room_id": row.room_id,
        "title": row.title,
        "scheduled_date": row.scheduled_date,
        "completed_date": row.completed_date,
        "status": row.status,
        "effective_status": _effective_inspection_status(row),
        "notes": row.notes,
        "findings": row.findings,
        "follow_up_actions": row.follow_up_actions,
        "assigned_to_user_id": row.assigned_to_user_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_inspections(
    session: Session,
    ctx: OrganisationContext,
    *,
    property_id: uuid.UUID | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    access.require_inspections_manage(ctx)
    property_ids = _property_ids(session, ctx, property_id)
    rows = list(
        session.scalars(
            select(PropertyInspection)
            .where(
                PropertyInspection.organisation_id == ctx.organisation_id,
                PropertyInspection.is_archived.is_(False),
                PropertyInspection.property_id.in_(property_ids) if property_ids else False,
            )
            .order_by(PropertyInspection.scheduled_date.desc())
        ).all()
    )
    if date_from:
        rows = [r for r in rows if r.scheduled_date >= date_from]
    if date_to:
        rows = [r for r in rows if r.scheduled_date <= date_to]
    if status:
        rows = [r for r in rows if _effective_inspection_status(r) == status]
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return {
        "items": [_inspection_out(session, row) for row in page_rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "upcoming": sum(1 for r in rows if _effective_inspection_status(r) == "scheduled"),
        "overdue": sum(1 for r in rows if _effective_inspection_status(r) == "overdue"),
    }


def create_inspection(session: Session, ctx: OrganisationContext, data: InspectionWrite) -> dict[str, Any]:
    access.require_inspections_manage(ctx)
    access.get_accessible_property(session, ctx, data.property_id)
    if data.status not in INSPECTION_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid inspection status")
    if data.room_id:
        access.assert_room_on_property(session, ctx, data.room_id, data.property_id)
    row = PropertyInspection(
        id=uuid.uuid4(),
        organisation_id=ctx.organisation_id,
        property_id=data.property_id,
        room_id=data.room_id,
        title=data.title.strip(),
        scheduled_date=data.scheduled_date,
        completed_date=data.completed_date,
        status=data.status,
        notes=data.notes,
        findings=data.findings,
        follow_up_actions=data.follow_up_actions,
        assigned_to_user_id=data.assigned_to_user_id,
        created_by_user_id=ctx.user_id,
    )
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.LANDLORD_INSPECTION_UPSERT,
        resource_type="property_inspection",
        resource_id=row.id,
        summary="Inspection created",
    )
    return _inspection_out(session, row)


def update_inspection(
    session: Session, ctx: OrganisationContext, inspection_id: uuid.UUID, data: InspectionWrite
) -> dict[str, Any]:
    access.require_inspections_manage(ctx)
    row = session.get(PropertyInspection, inspection_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.is_archived:
        raise HTTPException(status_code=404, detail="Inspection not found")
    access.get_accessible_property(session, ctx, row.property_id)
    access.get_accessible_property(session, ctx, data.property_id)
    if data.status not in INSPECTION_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid inspection status")
    if data.room_id:
        access.assert_room_on_property(session, ctx, data.room_id, data.property_id)
    row.property_id = data.property_id
    row.room_id = data.room_id
    row.title = data.title.strip()
    row.scheduled_date = data.scheduled_date
    row.completed_date = data.completed_date
    row.status = data.status
    row.notes = data.notes
    row.findings = data.findings
    row.follow_up_actions = data.follow_up_actions
    row.assigned_to_user_id = data.assigned_to_user_id
    if data.status == "completed" and row.completed_date is None:
        row.completed_date = date.today()
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.LANDLORD_INSPECTION_UPSERT,
        resource_type="property_inspection",
        resource_id=row.id,
        summary="Inspection updated",
    )
    return _inspection_out(session, row)


def get_inspection(session: Session, ctx: OrganisationContext, inspection_id: uuid.UUID) -> dict[str, Any]:
    access.require_inspections_manage(ctx)
    row = session.get(PropertyInspection, inspection_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.is_archived:
        raise HTTPException(status_code=404, detail="Inspection not found")
    access.get_accessible_property(session, ctx, row.property_id)
    return _inspection_out(session, row)


def list_repair_oversight(
    session: Session,
    ctx: OrganisationContext,
    *,
    property_id: uuid.UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    overdue_only: bool = False,
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    access.require_repairs_read(ctx)
    property_ids = _property_ids(session, ctx, property_id)
    rows = list(
        session.scalars(
            select(MaintenanceRequest)
            .where(
                MaintenanceRequest.organisation_id == ctx.organisation_id,
                MaintenanceRequest.property_id.in_(property_ids) if property_ids else False,
            )
            .order_by(MaintenanceRequest.created_at.desc())
        ).all()
    )
    now = datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []
    for row in rows:
        if status and row.status != status:
            continue
        if priority and row.priority != priority:
            continue
        is_overdue = bool(
            row.scheduled_visit_at
            and row.scheduled_visit_at < now
            and row.status in OPEN_REPAIR_STATUSES
        )
        if overdue_only and not is_overdue:
            continue
        prop = session.get(Property, row.property_id)
        items.append(
            {
                "id": str(row.id),
                "property_id": str(row.property_id),
                "property_name": prop.name if prop else None,
                "title": row.title,
                "priority": row.priority,
                "status": row.status,
                "assigned_user_id": str(row.assigned_user_id) if row.assigned_user_id else None,
                "scheduled_visit_at": row.scheduled_visit_at.isoformat() if row.scheduled_visit_at else None,
                "is_overdue": is_overdue,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "completion_notes": row.completion_summary,
            }
        )
    total = len(items)
    start = (page - 1) * page_size
    page_items = items[start : start + page_size]
    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "open": sum(1 for i in items if i["status"] in OPEN_REPAIR_STATUSES),
        "completed": sum(1 for i in items if i["status"] in COMPLETED_REPAIR_STATUSES),
        "overdue": sum(1 for i in items if i["is_overdue"]),
    }
