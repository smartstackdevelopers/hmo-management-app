"""F5.5 wellbeing services — private check-ins, routines, resources, navigator."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.catalogue import CommunityService
from app.db.models.wellbeing import (
    WellbeingCheckin,
    WellbeingDirectoryEntry,
    WellbeingResource,
    WellbeingResourceCompletion,
    WellbeingRoutine,
    WellbeingRoutineCompletion,
    WellbeingSavedResource,
)
from app.tenancy.context import OrganisationContext
from app.wellbeing.access import require_resource_admin, resolve_own_tenant
from app.wellbeing.constants import (
    DEFAULT_RESOURCES,
    DIRECTORY_CATEGORIES,
    DISCLAIMER,
    EXERCISE_CATEGORIES,
    MINDFULNESS_CATEGORIES,
    MOODS,
    NATIONAL_SUPPORT_LINKS,
    NAVIGATOR_CATEGORIES,
    ROUTINE_CATEGORIES,
)
from app.wellbeing.schemas import (
    CheckinOut,
    CheckinWrite,
    DashboardOut,
    DirectoryEntryOut,
    DirectoryEntryWrite,
    NavigatorCategoryOut,
    NavigatorResultOut,
    ResourceCompletionWrite,
    ResourceOut,
    ResourceWrite,
    RoutineOut,
    RoutineStatusWrite,
    RoutineWrite,
)


def _audit(session: Session, ctx: OrganisationContext, *, action: str, resource_type: str, resource_id, summary: str) -> None:
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


def disclaimer() -> dict[str, str]:
    return {"disclaimer": DISCLAIMER}


def _checkin_out(row: WellbeingCheckin) -> CheckinOut:
    return CheckinOut(
        id=row.id,
        checkin_date=row.checkin_date,
        mood=row.mood,
        energy_level=row.energy_level,
        stress_level=row.stress_level,
        notes=row.notes,
        skipped=row.skipped,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def upsert_checkin(session: Session, ctx: OrganisationContext, data: CheckinWrite) -> CheckinOut:
    tenant = resolve_own_tenant(session, ctx)
    day = data.checkin_date or date.today()
    if data.mood is not None and data.mood not in MOODS:
        raise HTTPException(status_code=422, detail="Invalid mood")
    if data.skipped and (data.mood or data.energy_level or data.stress_level or data.notes):
        # Allow skip with empty optional fields only — clear sensitive fields.
        pass
    row = session.scalar(
        select(WellbeingCheckin).where(
            WellbeingCheckin.organisation_id == ctx.organisation_id,
            WellbeingCheckin.tenant_id == tenant.id,
            WellbeingCheckin.checkin_date == day,
        )
    )
    if row is None:
        row = WellbeingCheckin(
            organisation_id=ctx.organisation_id,
            tenant_id=tenant.id,
            checkin_date=day,
        )
        session.add(row)
    row.mood = None if data.skipped else data.mood
    row.energy_level = None if data.skipped else data.energy_level
    row.stress_level = None if data.skipped else data.stress_level
    row.notes = None if data.skipped else data.notes
    row.skipped = bool(data.skipped)
    session.flush()
    _audit(session, ctx, action=audit_events.WELLBEING_CHECKIN_UPSERT, resource_type="wellbeing_checkin", resource_id=row.id, summary="Wellbeing check-in saved")
    return _checkin_out(row)


def get_today_checkin(session: Session, ctx: OrganisationContext) -> CheckinOut | None:
    tenant = resolve_own_tenant(session, ctx)
    row = session.scalar(
        select(WellbeingCheckin).where(
            WellbeingCheckin.organisation_id == ctx.organisation_id,
            WellbeingCheckin.tenant_id == tenant.id,
            WellbeingCheckin.checkin_date == date.today(),
        )
    )
    return _checkin_out(row) if row else None


def list_checkins(
    session: Session, ctx: OrganisationContext, *, days: int, page: int, page_size: int
) -> dict[str, Any]:
    tenant = resolve_own_tenant(session, ctx)
    days = min(90, max(1, days))
    page = max(1, page)
    page_size = min(50, max(1, page_size))
    start = date.today().fromordinal(date.today().toordinal() - days + 1)
    stmt = (
        select(WellbeingCheckin)
        .where(
            WellbeingCheckin.organisation_id == ctx.organisation_id,
            WellbeingCheckin.tenant_id == tenant.id,
            WellbeingCheckin.checkin_date >= start,
        )
        .order_by(WellbeingCheckin.checkin_date.desc())
    )
    rows = list(session.scalars(stmt))
    total = len(rows)
    offset = (page - 1) * page_size
    slice_rows = rows[offset : offset + page_size]
    return {
        "items": [_checkin_out(r) for r in slice_rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "disclaimer": DISCLAIMER,
    }


def delete_checkin(session: Session, ctx: OrganisationContext, checkin_id: uuid.UUID) -> dict[str, str]:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(WellbeingCheckin, checkin_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Check-in not found")
    session.delete(row)
    session.flush()
    _audit(session, ctx, action=audit_events.WELLBEING_CHECKIN_DELETE, resource_type="wellbeing_checkin", resource_id=checkin_id, summary="Wellbeing check-in deleted")
    return {"status": "deleted"}


def _routine_applies(row: WellbeingRoutine, day: date) -> bool:
    if not row.is_active:
        return False
    if row.recurrence == "one_time":
        return row.one_time_date == day
    if row.recurrence == "daily":
        return True
    if row.recurrence == "weekdays":
        return day.weekday() < 5
    if row.recurrence == "weekly":
        mask = row.weekday_mask if row.weekday_mask is not None else (1 << day.weekday())
        return bool(mask & (1 << day.weekday()))
    return False


def _routine_out(row: WellbeingRoutine, today_status: str | None = None) -> RoutineOut:
    return RoutineOut(
        id=row.id,
        title=row.title,
        description=row.description,
        category=row.category,
        start_time=row.start_time,
        end_time=row.end_time,
        recurrence=row.recurrence,
        weekday_mask=row.weekday_mask,
        one_time_date=row.one_time_date,
        is_active=row.is_active,
        reminder_enabled=row.reminder_enabled,
        reminder_minutes_before=row.reminder_minutes_before,
        today_status=today_status,
    )


def _validate_routine(data: RoutineWrite) -> None:
    if data.category not in ROUTINE_CATEGORIES:
        raise HTTPException(status_code=422, detail="Invalid routine category")
    if data.recurrence not in {"daily", "weekdays", "weekly", "one_time"}:
        raise HTTPException(status_code=422, detail="Invalid recurrence")
    if data.end_time is not None and data.end_time <= data.start_time:
        raise HTTPException(status_code=422, detail="end_time must be after start_time")
    if data.recurrence == "one_time" and data.one_time_date is None:
        raise HTTPException(status_code=422, detail="one_time_date required")
    if data.reminder_enabled and data.reminder_minutes_before is None:
        raise HTTPException(status_code=422, detail="reminder_minutes_before required when reminders enabled")


def create_routine(session: Session, ctx: OrganisationContext, data: RoutineWrite) -> RoutineOut:
    tenant = resolve_own_tenant(session, ctx)
    _validate_routine(data)
    row = WellbeingRoutine(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        title=data.title.strip(),
        description=data.description,
        category=data.category,
        start_time=data.start_time,
        end_time=data.end_time,
        recurrence=data.recurrence,
        weekday_mask=data.weekday_mask,
        one_time_date=data.one_time_date,
        reminder_enabled=data.reminder_enabled,
        reminder_minutes_before=data.reminder_minutes_before if data.reminder_enabled else None,
    )
    session.add(row)
    session.flush()
    if row.reminder_enabled:
        _enqueue_routine_reminder(session, ctx, row)
    _audit(session, ctx, action=audit_events.WELLBEING_ROUTINE_UPSERT, resource_type="wellbeing_routine", resource_id=row.id, summary="Routine created")
    return _routine_out(row)


def update_routine(session: Session, ctx: OrganisationContext, routine_id: uuid.UUID, data: RoutineWrite) -> RoutineOut:
    tenant = resolve_own_tenant(session, ctx)
    _validate_routine(data)
    row = session.get(WellbeingRoutine, routine_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Routine not found")
    row.title = data.title.strip()
    row.description = data.description
    row.category = data.category
    row.start_time = data.start_time
    row.end_time = data.end_time
    row.recurrence = data.recurrence
    row.weekday_mask = data.weekday_mask
    row.one_time_date = data.one_time_date
    was_enabled = row.reminder_enabled
    row.reminder_enabled = data.reminder_enabled
    row.reminder_minutes_before = data.reminder_minutes_before if data.reminder_enabled else None
    session.add(row)
    session.flush()
    if row.reminder_enabled and (not was_enabled or True):
        _enqueue_routine_reminder(session, ctx, row)
    _audit(session, ctx, action=audit_events.WELLBEING_ROUTINE_UPSERT, resource_type="wellbeing_routine", resource_id=row.id, summary="Routine updated")
    return _routine_out(row)


def delete_routine(session: Session, ctx: OrganisationContext, routine_id: uuid.UUID) -> dict[str, str]:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(WellbeingRoutine, routine_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Routine not found")
    row.is_active = False
    row.reminder_enabled = False
    session.add(row)
    session.flush()
    return {"status": "deleted"}


def list_routines(session: Session, ctx: OrganisationContext, *, day: date | None = None) -> dict[str, Any]:
    tenant = resolve_own_tenant(session, ctx)
    day = day or date.today()
    rows = list(
        session.scalars(
            select(WellbeingRoutine).where(
                WellbeingRoutine.organisation_id == ctx.organisation_id,
                WellbeingRoutine.tenant_id == tenant.id,
                WellbeingRoutine.is_active.is_(True),
            )
        )
    )
    completions = {
        c.routine_id: c.status
        for c in session.scalars(
            select(WellbeingRoutineCompletion).where(
                WellbeingRoutineCompletion.organisation_id == ctx.organisation_id,
                WellbeingRoutineCompletion.tenant_id == tenant.id,
                WellbeingRoutineCompletion.activity_date == day,
            )
        )
    }
    items = [_routine_out(r, completions.get(r.id)) for r in rows if _routine_applies(r, day)]
    items.sort(key=lambda item: item.start_time)
    completed = sum(1 for i in items if i.today_status == "completed")
    skipped = sum(1 for i in items if i.today_status == "skipped")
    return {
        "items": items,
        "progress": {
            "planned": len(items),
            "completed": completed,
            "skipped": skipped,
            "remaining": max(0, len(items) - completed - skipped),
        },
        "date": day.isoformat(),
        "note": "Missed routines are okay. This planner is flexible support, not a requirement.",
    }


def set_routine_status(
    session: Session, ctx: OrganisationContext, routine_id: uuid.UUID, data: RoutineStatusWrite
) -> dict[str, Any]:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(WellbeingRoutine, routine_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Routine not found")
    day = data.activity_date or date.today()
    existing = session.scalar(
        select(WellbeingRoutineCompletion).where(
            WellbeingRoutineCompletion.routine_id == routine_id,
            WellbeingRoutineCompletion.activity_date == day,
        )
    )
    if existing is None:
        existing = WellbeingRoutineCompletion(
            organisation_id=ctx.organisation_id,
            tenant_id=tenant.id,
            routine_id=routine_id,
            activity_date=day,
            status=data.status,
        )
        session.add(existing)
    existing.status = data.status
    existing.completed_at = datetime.now(timezone.utc) if data.status == "completed" else None
    session.flush()
    return {"status": data.status, "activity_date": day.isoformat()}


def _enqueue_routine_reminder(session: Session, ctx: OrganisationContext, row: WellbeingRoutine) -> None:
    """Queue a push via existing F4.3 infrastructure when reminders are enabled."""
    if not row.reminder_enabled:
        return
    try:
        from app.push.delivery import enqueue_push_for_target

        enqueue_push_for_target(
            session,
            organisation_id=ctx.organisation_id,
            recipient_user_id=ctx.user_id,
            target_type="wellbeing_routine_reminder",
            target_id=row.id,
            idempotency_base=f"wellbeing-routine-{row.id}-{date.today().isoformat()}-{row.start_time.isoformat()}",
        )
    except Exception:  # noqa: BLE001
        # Reminder failure must not block routine save.
        return


def ensure_default_resources(session: Session, ctx: OrganisationContext) -> int:
    existing = session.scalar(
        select(func.count()).select_from(WellbeingResource).where(
            WellbeingResource.organisation_id == ctx.organisation_id
        )
    ) or 0
    if existing:
        return 0
    created = 0
    for item in DEFAULT_RESOURCES:
        session.add(
            WellbeingResource(
                organisation_id=ctx.organisation_id,
                kind=item["kind"],
                category=item["category"],
                title=item["title"],
                description=item.get("description"),
                instructions=item.get("instructions"),
                duration_minutes=item.get("duration_minutes"),
                activity_level=item.get("activity_level"),
                equipment=item.get("equipment"),
                safety_notes=item.get("safety_notes"),
                source_name=item.get("source_name"),
                verification_status=item.get("verification_status") or "verified",
                is_active=True,
            )
        )
        created += 1
    session.flush()
    return created


def _resource_out(row: WellbeingResource, saved_ids: set[uuid.UUID]) -> ResourceOut:
    return ResourceOut(
        id=row.id,
        kind=row.kind,
        category=row.category,
        title=row.title,
        description=row.description,
        instructions=row.instructions,
        duration_minutes=row.duration_minutes,
        activity_level=row.activity_level,
        equipment=row.equipment,
        safety_notes=row.safety_notes,
        source_name=row.source_name,
        source_url=row.source_url,
        verification_status=row.verification_status,
        is_saved=row.id in saved_ids,
    )


def list_resources(
    session: Session, ctx: OrganisationContext, *, kind: str | None, category: str | None
) -> dict[str, Any]:
    tenant = resolve_own_tenant(session, ctx)
    ensure_default_resources(session, ctx)
    if kind and kind not in {"exercise", "mindfulness"}:
        raise HTTPException(status_code=422, detail="Invalid kind")
    stmt = select(WellbeingResource).where(
        WellbeingResource.organisation_id == ctx.organisation_id,
        WellbeingResource.is_active.is_(True),
    )
    if kind:
        stmt = stmt.where(WellbeingResource.kind == kind)
    if category:
        stmt = stmt.where(WellbeingResource.category == category)
    rows = list(session.scalars(stmt.order_by(WellbeingResource.title.asc())))
    saved_ids = {
        s.resource_id
        for s in session.scalars(
            select(WellbeingSavedResource).where(
                WellbeingSavedResource.organisation_id == ctx.organisation_id,
                WellbeingSavedResource.tenant_id == tenant.id,
            )
        )
    }
    return {
        "items": [_resource_out(r, saved_ids) for r in rows],
        "exercise_categories": list(EXERCISE_CATEGORIES),
        "mindfulness_categories": list(MINDFULNESS_CATEGORIES),
        "disclaimer": DISCLAIMER,
    }


def save_resource(session: Session, ctx: OrganisationContext, resource_id: uuid.UUID) -> dict[str, str]:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(WellbeingResource, resource_id)
    if row is None or row.organisation_id != ctx.organisation_id or not row.is_active:
        raise HTTPException(status_code=404, detail="Resource not found")
    existing = session.scalar(
        select(WellbeingSavedResource).where(
            WellbeingSavedResource.tenant_id == tenant.id, WellbeingSavedResource.resource_id == resource_id
        )
    )
    if existing:
        return {"status": "already_saved"}
    session.add(
        WellbeingSavedResource(organisation_id=ctx.organisation_id, tenant_id=tenant.id, resource_id=resource_id)
    )
    session.flush()
    return {"status": "saved"}


def unsave_resource(session: Session, ctx: OrganisationContext, resource_id: uuid.UUID) -> dict[str, str]:
    tenant = resolve_own_tenant(session, ctx)
    row = session.scalar(
        select(WellbeingSavedResource).where(
            WellbeingSavedResource.tenant_id == tenant.id, WellbeingSavedResource.resource_id == resource_id
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Saved resource not found")
    session.delete(row)
    session.flush()
    return {"status": "removed"}


def complete_resource(
    session: Session, ctx: OrganisationContext, resource_id: uuid.UUID, data: ResourceCompletionWrite
) -> dict[str, str]:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(WellbeingResource, resource_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Resource not found")
    session.add(
        WellbeingResourceCompletion(
            organisation_id=ctx.organisation_id,
            tenant_id=tenant.id,
            resource_id=resource_id,
            status=data.status,
            completed_at=datetime.now(timezone.utc),
        )
    )
    session.flush()
    return {"status": data.status}


def list_saved_resources(session: Session, ctx: OrganisationContext, *, kind: str | None = None) -> dict[str, Any]:
    tenant = resolve_own_tenant(session, ctx)
    stmt = (
        select(WellbeingResource)
        .join(WellbeingSavedResource, WellbeingSavedResource.resource_id == WellbeingResource.id)
        .where(
            WellbeingSavedResource.tenant_id == tenant.id,
            WellbeingResource.organisation_id == ctx.organisation_id,
            WellbeingResource.is_active.is_(True),
        )
    )
    if kind:
        stmt = stmt.where(WellbeingResource.kind == kind)
    rows = list(session.scalars(stmt.order_by(WellbeingSavedResource.created_at.desc())))
    saved_ids = {r.id for r in rows}
    return {"items": [_resource_out(r, saved_ids) for r in rows], "disclaimer": DISCLAIMER}


def admin_upsert_resource(
    session: Session, ctx: OrganisationContext, data: ResourceWrite, resource_id: uuid.UUID | None = None
) -> ResourceOut:
    require_resource_admin(ctx)
    if data.kind == "exercise" and data.category not in EXERCISE_CATEGORIES:
        raise HTTPException(status_code=422, detail="Invalid exercise category")
    if data.kind == "mindfulness" and data.category not in MINDFULNESS_CATEGORIES:
        raise HTTPException(status_code=422, detail="Invalid mindfulness category")
    if data.verification_status not in {"unverified", "verified", "rejected"}:
        raise HTTPException(status_code=422, detail="Invalid verification_status")
    row = session.get(WellbeingResource, resource_id) if resource_id else None
    if resource_id and (row is None or row.organisation_id != ctx.organisation_id):
        raise HTTPException(status_code=404, detail="Resource not found")
    if row is None:
        row = WellbeingResource(organisation_id=ctx.organisation_id, kind=data.kind, category=data.category, title=data.title)
        session.add(row)
    row.kind = data.kind
    row.category = data.category
    row.title = data.title.strip()
    row.description = data.description
    row.instructions = data.instructions
    row.duration_minutes = data.duration_minutes
    row.activity_level = data.activity_level
    row.equipment = data.equipment
    row.safety_notes = data.safety_notes
    row.source_name = data.source_name
    row.source_url = data.source_url
    row.verification_status = data.verification_status
    row.is_active = data.is_active
    session.flush()
    _audit(session, ctx, action=audit_events.WELLBEING_RESOURCE_UPSERT, resource_type="wellbeing_resource", resource_id=row.id, summary="Wellbeing resource upserted")
    return _resource_out(row, set())


def _directory_out(row: WellbeingDirectoryEntry) -> DirectoryEntryOut:
    return DirectoryEntryOut(
        id=row.id,
        name=row.name,
        description=row.description,
        category=row.category,
        address=row.address,
        contact_info=row.contact_info,
        opening_hours=row.opening_hours,
        eligibility=row.eligibility,
        referral_info=row.referral_info,
        source_url=row.source_url,
        is_clinical=row.is_clinical,
        verification_status=row.verification_status,
        last_verified_at=row.last_verified_at,
        from_community_directory=row.community_service_id is not None,
    )


def list_directory(session: Session, ctx: OrganisationContext, *, category: str | None = None) -> dict[str, Any]:
    resolve_own_tenant(session, ctx)
    stmt = select(WellbeingDirectoryEntry).where(
        WellbeingDirectoryEntry.organisation_id == ctx.organisation_id,
        WellbeingDirectoryEntry.is_active.is_(True),
    )
    if category:
        stmt = stmt.where(WellbeingDirectoryEntry.category == category)
    entries = [_directory_out(r) for r in session.scalars(stmt.order_by(WellbeingDirectoryEntry.name.asc()))]

    # Also surface published community local_service listings (F5.1) without inventing data.
    community_rows = list(
        session.scalars(
            select(CommunityService).where(
                CommunityService.organisation_id == ctx.organisation_id,
                CommunityService.is_published.is_(True),
                CommunityService.category == "local_service",
            )
        )
    )
    for svc in community_rows:
        entries.append(
            DirectoryEntryOut(
                id=svc.id,
                name=svc.name,
                description=svc.description,
                category="general_support",
                address=svc.address_line,
                contact_info=svc.contact,
                opening_hours=svc.opening_hours,
                eligibility=svc.eligibility,
                referral_info=svc.referral_requirements,
                source_url=None,
                is_clinical=False,
                verification_status="verified" if svc.verification_status == "verified" else "unverified",
                last_verified_at=svc.verified_at,
                from_community_directory=True,
            )
        )
    return {
        "items": entries,
        "categories": list(DIRECTORY_CATEGORIES),
        "disclaimer": DISCLAIMER,
        "note": "Community support is distinct from clinical healthcare. Entries are organisation-verified where marked.",
    }


def admin_upsert_directory(
    session: Session, ctx: OrganisationContext, data: DirectoryEntryWrite, entry_id: uuid.UUID | None = None
) -> DirectoryEntryOut:
    require_resource_admin(ctx)
    if data.category not in DIRECTORY_CATEGORIES:
        raise HTTPException(status_code=422, detail="Invalid directory category")
    if data.verification_status not in {"unverified", "verified", "rejected"}:
        raise HTTPException(status_code=422, detail="Invalid verification_status")
    row = session.get(WellbeingDirectoryEntry, entry_id) if entry_id else None
    if entry_id and (row is None or row.organisation_id != ctx.organisation_id):
        raise HTTPException(status_code=404, detail="Directory entry not found")
    if row is None:
        row = WellbeingDirectoryEntry(organisation_id=ctx.organisation_id, name=data.name, category=data.category)
        session.add(row)
    row.name = data.name.strip()
    row.description = data.description
    row.category = data.category
    row.address = data.address
    row.contact_info = data.contact_info
    row.opening_hours = data.opening_hours
    row.eligibility = data.eligibility
    row.referral_info = data.referral_info
    row.source_url = data.source_url
    row.community_service_id = data.community_service_id
    row.is_clinical = data.is_clinical
    row.verification_status = data.verification_status
    row.is_active = data.is_active
    if data.verification_status == "verified":
        row.last_verified_at = datetime.now(timezone.utc)
    session.flush()
    _audit(session, ctx, action=audit_events.WELLBEING_DIRECTORY_UPSERT, resource_type="wellbeing_directory_entry", resource_id=row.id, summary="Wellbeing directory entry upserted")
    return _directory_out(row)


def list_navigator_categories() -> dict[str, Any]:
    return {
        "items": [NavigatorCategoryOut(id=c["id"], title=c["title"], description=c["description"]) for c in NAVIGATOR_CATEGORIES],
        "disclaimer": DISCLAIMER,
    }


def navigate(session: Session, ctx: OrganisationContext, category_id: str) -> NavigatorResultOut:
    resolve_own_tenant(session, ctx)
    cat = next((c for c in NAVIGATOR_CATEGORIES if c["id"] == category_id), None)
    if cat is None:
        raise HTTPException(status_code=404, detail="Navigator category not found")
    directory = list_directory(session, ctx)
    mapped = set(cat["maps_to_directory"])
    entries = [e for e in directory["items"] if e.category in mapped] if mapped else []
    national = [link for link in NATIONAL_SUPPORT_LINKS if link["id"] in cat["national_link_ids"]]
    crisis = None
    if category_id == "crisis":
        crisis = (
            "If you are in immediate danger, contact emergency services now (999 in the UK). "
            "HMore check-ins are not an emergency monitoring system."
        )
    return NavigatorResultOut(
        disclaimer=DISCLAIMER,
        category=NavigatorCategoryOut(id=cat["id"], title=cat["title"], description=cat["description"]),
        directory_entries=entries,
        national_links=national,
        crisis_guidance=crisis,
    )


def dashboard(session: Session, ctx: OrganisationContext) -> DashboardOut:
    tenant = resolve_own_tenant(session, ctx)
    today = get_today_checkin(session, ctx)
    history = list_checkins(session, ctx, days=14, page=1, page_size=7)
    routines = list_routines(session, ctx, day=date.today())
    ensure_default_resources(session, ctx)
    saved_ex = list_saved_resources(session, ctx, kind="exercise")
    saved_mf = list_saved_resources(session, ctx, kind="mindfulness")
    directory = list_directory(session, ctx)
    latest_mood = today.mood if today and not today.skipped else None
    if latest_mood is None:
        for item in history["items"]:
            if item.mood and not item.skipped:
                latest_mood = item.mood
                break
    return DashboardOut(
        disclaimer=DISCLAIMER,
        today_checkin=today,
        latest_mood=latest_mood,
        today_routines=routines["items"],
        routine_progress=routines["progress"],
        saved_exercise_count=len(saved_ex["items"]),
        saved_mindfulness_count=len(saved_mf["items"]),
        recent_checkins=history["items"],
        local_support_preview=directory["items"][:5],
    )
