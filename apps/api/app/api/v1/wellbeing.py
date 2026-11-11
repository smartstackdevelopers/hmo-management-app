"""Tenant wellbeing APIs (F5.5) — private check-ins; staff manage public resources."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context
from app.wellbeing import service as wellbeing
from app.wellbeing.schemas import (
    CheckinWrite,
    DirectoryEntryWrite,
    ResourceCompletionWrite,
    ResourceWrite,
    RoutineStatusWrite,
    RoutineWrite,
)

router = APIRouter(prefix="/wellbeing", tags=["wellbeing"])


@router.get("/disclaimer")
def get_disclaimer():
    return wellbeing.disclaimer()


@router.get("/dashboard")
def get_dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.dashboard(session, org)


@router.get("/checkins/today")
def today_checkin(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.get_today_checkin(session, org)


@router.put("/checkins")
def put_checkin(
    body: CheckinWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.upsert_checkin(session, org, body)


@router.get("/checkins")
def get_checkins(
    days: int = Query(default=30, ge=1, le=90),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=50),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.list_checkins(session, org, days=days, page=page, page_size=page_size)


@router.delete("/checkins/{checkin_id}")
def delete_checkin(
    checkin_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.delete_checkin(session, org, checkin_id)


@router.get("/routines")
def get_routines(
    day: date | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.list_routines(session, org, day=day)


@router.post("/routines", status_code=201)
def post_routine(
    body: RoutineWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.create_routine(session, org, body)


@router.put("/routines/{routine_id}")
def put_routine(
    routine_id: uuid.UUID,
    body: RoutineWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.update_routine(session, org, routine_id, body)


@router.delete("/routines/{routine_id}")
def delete_routine(
    routine_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.delete_routine(session, org, routine_id)


@router.post("/routines/{routine_id}/status")
def routine_status(
    routine_id: uuid.UUID,
    body: RoutineStatusWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.set_routine_status(session, org, routine_id, body)


@router.get("/resources")
def get_resources(
    kind: str | None = None,
    category: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.list_resources(session, org, kind=kind, category=category)


@router.get("/resources/saved")
def get_saved_resources(
    kind: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.list_saved_resources(session, org, kind=kind)


@router.post("/resources/{resource_id}/save")
def save_resource(
    resource_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.save_resource(session, org, resource_id)


@router.delete("/resources/{resource_id}/save")
def unsave_resource(
    resource_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.unsave_resource(session, org, resource_id)


@router.post("/resources/{resource_id}/complete")
def complete_resource(
    resource_id: uuid.UUID,
    body: ResourceCompletionWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.complete_resource(session, org, resource_id, body)


@router.post("/admin/resources", status_code=201)
def admin_create_resource(
    body: ResourceWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.admin_upsert_resource(session, org, body)


@router.put("/admin/resources/{resource_id}")
def admin_update_resource(
    resource_id: uuid.UUID,
    body: ResourceWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.admin_upsert_resource(session, org, body, resource_id=resource_id)


@router.get("/directory")
def get_directory(
    category: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.list_directory(session, org, category=category)


@router.post("/admin/directory", status_code=201)
def admin_create_directory(
    body: DirectoryEntryWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.admin_upsert_directory(session, org, body)


@router.put("/admin/directory/{entry_id}")
def admin_update_directory(
    entry_id: uuid.UUID,
    body: DirectoryEntryWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.admin_upsert_directory(session, org, body, entry_id=entry_id)


@router.get("/navigator/categories")
def navigator_categories():
    return wellbeing.list_navigator_categories()


@router.get("/navigator/{category_id}")
def navigator_category(
    category_id: str,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return wellbeing.navigate(session, org, category_id)
