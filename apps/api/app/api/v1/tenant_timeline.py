"""F2.9 tenant timeline, meetings, appointments, follow-ups, needs/goals."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.tenant_timeline import service as tl_service
from app.tenant_timeline.schemas import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentUpdate,
    MeetingCancelRequest,
    MeetingCompleteRequest,
    MeetingCreate,
    MeetingUpdate,
    TenantFollowUpCompleteRequest,
    TenantFollowUpCreate,
    TenantFollowUpUpdate,
    TenantNeedGoalCreate,
    TenantNeedGoalUpdate,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/tenants/{tenant_id}/timeline", tags=["tenant-timeline"])


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("", response_model=dict[str, Any])
def get_timeline(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("newest"),
    activity_type: list[str] | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    assigned_user_id: uuid.UUID | None = Query(None),
    q: str | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.get_tenant_timeline(
        session,
        org,
        tenant_id,
        page=page,
        page_size=page_size,
        sort=sort,
        activity_types=activity_type,
        date_from=date_from,
        date_to=date_to,
        assigned_user_id=assigned_user_id,
        search=q,
    )


@router.post("/meetings", response_model=dict[str, Any], status_code=201)
def create_meeting(
    tenant_id: uuid.UUID,
    body: MeetingCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.create_meeting(session, org, tenant_id, body)


@router.get("/meetings", response_model=dict[str, Any])
def list_meetings(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = tl_service.list_meetings(session, org, tenant_id, page=page, page_size=page_size)
    return _page(rows, page, page_size, total)


@router.get("/meetings/{meeting_id}", response_model=dict[str, Any])
def get_meeting(
    tenant_id: uuid.UUID,
    meeting_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.get_meeting(session, org, tenant_id, meeting_id)


@router.patch("/meetings/{meeting_id}", response_model=dict[str, Any])
def patch_meeting(
    tenant_id: uuid.UUID,
    meeting_id: uuid.UUID,
    body: MeetingUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.update_meeting(session, org, tenant_id, meeting_id, body)


@router.post("/meetings/{meeting_id}/complete", response_model=dict[str, Any])
def complete_meeting_route(
    tenant_id: uuid.UUID,
    meeting_id: uuid.UUID,
    body: MeetingCompleteRequest | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.complete_meeting(
        session, org, tenant_id, meeting_id, body or MeetingCompleteRequest()
    )


@router.post("/meetings/{meeting_id}/cancel", response_model=dict[str, Any])
def cancel_meeting_route(
    tenant_id: uuid.UUID,
    meeting_id: uuid.UUID,
    body: MeetingCancelRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.cancel_meeting(session, org, tenant_id, meeting_id, body)


@router.post("/appointments", response_model=dict[str, Any], status_code=201)
def create_appointment(
    tenant_id: uuid.UUID,
    body: AppointmentCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.create_appointment(session, org, tenant_id, body)


@router.get("/appointments", response_model=dict[str, Any])
def list_appointments(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = tl_service.list_appointments(session, org, tenant_id, page=page, page_size=page_size)
    return _page(rows, page, page_size, total)


@router.get("/appointments/{appointment_id}", response_model=dict[str, Any])
def get_appointment(
    tenant_id: uuid.UUID,
    appointment_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.get_appointment(session, org, tenant_id, appointment_id)


@router.patch("/appointments/{appointment_id}", response_model=dict[str, Any])
def patch_appointment(
    tenant_id: uuid.UUID,
    appointment_id: uuid.UUID,
    body: AppointmentUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.update_appointment(session, org, tenant_id, appointment_id, body)


@router.post("/appointments/{appointment_id}/cancel", response_model=dict[str, Any])
def cancel_appointment_route(
    tenant_id: uuid.UUID,
    appointment_id: uuid.UUID,
    body: AppointmentCancelRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.cancel_appointment(session, org, tenant_id, appointment_id, body)


@router.post("/follow-ups", response_model=dict[str, Any], status_code=201)
def create_follow_up(
    tenant_id: uuid.UUID,
    body: TenantFollowUpCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.create_follow_up(session, org, tenant_id, body)


@router.get("/follow-ups", response_model=dict[str, Any])
def list_follow_ups(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    overdue_only: bool = Query(False),
    upcoming_only: bool = Query(False),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = tl_service.list_follow_ups(
        session,
        org,
        tenant_id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        overdue_only=overdue_only,
        upcoming_only=upcoming_only,
    )
    return _page(rows, page, page_size, total)


@router.get("/follow-ups/{follow_up_id}", response_model=dict[str, Any])
def get_follow_up(
    tenant_id: uuid.UUID,
    follow_up_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.get_follow_up(session, org, tenant_id, follow_up_id)


@router.patch("/follow-ups/{follow_up_id}", response_model=dict[str, Any])
def patch_follow_up(
    tenant_id: uuid.UUID,
    follow_up_id: uuid.UUID,
    body: TenantFollowUpUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.update_follow_up(session, org, tenant_id, follow_up_id, body)


@router.post("/follow-ups/{follow_up_id}/complete", response_model=dict[str, Any])
def complete_follow_up_route(
    tenant_id: uuid.UUID,
    follow_up_id: uuid.UUID,
    body: TenantFollowUpCompleteRequest | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.complete_follow_up(
        session, org, tenant_id, follow_up_id, body or TenantFollowUpCompleteRequest()
    )


@router.post("/needs-goals", response_model=dict[str, Any], status_code=201)
def create_need_goal(
    tenant_id: uuid.UUID,
    body: TenantNeedGoalCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.create_need_goal(session, org, tenant_id, body)


@router.get("/needs-goals", response_model=dict[str, Any])
def list_need_goals(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = tl_service.list_need_goals(session, org, tenant_id, page=page, page_size=page_size)
    return _page(rows, page, page_size, total)


@router.get("/needs-goals/{need_goal_id}", response_model=dict[str, Any])
def get_need_goal(
    tenant_id: uuid.UUID,
    need_goal_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.get_need_goal(session, org, tenant_id, need_goal_id)


@router.patch("/needs-goals/{need_goal_id}", response_model=dict[str, Any])
def patch_need_goal(
    tenant_id: uuid.UUID,
    need_goal_id: uuid.UUID,
    body: TenantNeedGoalUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return tl_service.update_need_goal(session, org, tenant_id, need_goal_id, body)
