"""F2.4 incident, follow-up, and workload APIs."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.incidents import service as incident_service
from app.incidents.schemas import (
    FollowUpCreate,
    FollowUpOut,
    FollowUpUpdate,
    IncidentCreate,
    IncidentHistoryOut,
    IncidentOut,
    IncidentUpdate,
    WorkloadResponse,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter()
incidents_router = APIRouter(prefix="/incidents", tags=["incidents"])
follow_ups_router = APIRouter(prefix="/incident-follow-ups", tags=["incident-follow-ups"])
workload_router = APIRouter(prefix="/workload", tags=["workload"])


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@incidents_router.post("", response_model=IncidentOut, status_code=201)
def create_incident(
    body: IncidentCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return incident_service.incident_out_dict(
        session, incident_service.create_incident(session, org, body)
    )


@incidents_router.get("", response_model=dict[str, Any])
def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    q: str | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = incident_service.list_incidents(
        session,
        org,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        category=category,
        severity=severity,
        q=q,
    )
    return _page(
        [incident_service.incident_out_dict(session, row) for row in rows],
        page,
        page_size,
        total,
    )


@incidents_router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return incident_service.incident_out_dict(
        session, incident_service.get_incident(session, org, incident_id)
    )


@incidents_router.patch("/{incident_id}", response_model=IncidentOut)
def patch_incident(
    incident_id: uuid.UUID,
    body: IncidentUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return incident_service.incident_out_dict(
        session, incident_service.update_incident(session, org, incident_id, body)
    )


@incidents_router.post("/{incident_id}/submit", response_model=IncidentOut)
def submit_incident(
    incident_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return incident_service.incident_out_dict(
        session, incident_service.transition_incident(session, org, incident_id, "submitted")
    )


@incidents_router.get("/{incident_id}/history", response_model=list[IncidentHistoryOut])
def incident_history(
    incident_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return incident_service.list_incident_history(session, org, incident_id)


@incidents_router.post("/{incident_id}/follow-ups", response_model=FollowUpOut, status_code=201)
def create_follow_up(
    incident_id: uuid.UUID,
    body: FollowUpCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return incident_service.create_follow_up(session, org, incident_id, body)


@incidents_router.get("/{incident_id}/follow-ups", response_model=dict[str, Any])
def list_incident_follow_ups(
    incident_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = incident_service.list_follow_ups(
        session, org, page=page, page_size=page_size, incident_id=incident_id
    )
    return _page(
        [FollowUpOut.model_validate(row).model_dump(mode="json") for row in rows],
        page,
        page_size,
        total,
    )


@follow_ups_router.get("", response_model=dict[str, Any])
def list_follow_ups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    overdue_only: bool = Query(False),
    assigned_user_id: uuid.UUID | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = incident_service.list_follow_ups(
        session,
        org,
        page=page,
        page_size=page_size,
        overdue_only=overdue_only,
        assigned_user_id=assigned_user_id,
    )
    return _page(
        [FollowUpOut.model_validate(row).model_dump(mode="json") for row in rows],
        page,
        page_size,
        total,
    )


@follow_ups_router.get("/{follow_up_id}", response_model=FollowUpOut)
def get_follow_up(
    follow_up_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return incident_service.get_follow_up(session, org, follow_up_id)


@follow_ups_router.patch("/{follow_up_id}", response_model=FollowUpOut)
def patch_follow_up(
    follow_up_id: uuid.UUID,
    body: FollowUpUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return incident_service.update_follow_up(session, org, follow_up_id, body)


@follow_ups_router.post("/{follow_up_id}/complete", response_model=FollowUpOut)
def complete_follow_up(
    follow_up_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return incident_service.update_follow_up(
        session, org, follow_up_id, FollowUpUpdate(status="completed")
    )


@workload_router.get("", response_model=WorkloadResponse)
def get_workload(
    staff_user_id: uuid.UUID | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> WorkloadResponse:
    return incident_service.get_workload(session, org, staff_user_id=staff_user_id)


@workload_router.get("/me", response_model=WorkloadResponse)
def get_my_workload(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> WorkloadResponse:
    return incident_service.get_workload(session, org, staff_user_id=org.user_id)


router.include_router(incidents_router)
router.include_router(follow_ups_router)
router.include_router(workload_router)
