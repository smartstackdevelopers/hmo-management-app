"""F2.5 housing application, waiting-list, and approval APIs."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.housing import service as housing_service
from app.housing.schemas import (
    ApplicationCreate,
    ApplicationHistoryOut,
    ApplicationOut,
    ApplicationUpdate,
    DecisionCreate,
    DecisionOut,
    InformationRequiredRequest,
    WaitingListAdd,
    WaitingListOut,
    WaitingListUpdate,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter()
applications_router = APIRouter(prefix="/housing-applications", tags=["housing-applications"])
waiting_list_router = APIRouter(prefix="/waiting-list", tags=["waiting-list"])


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@applications_router.post("", response_model=ApplicationOut, status_code=201)
def create_application(
    body: ApplicationCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return housing_service.application_out_dict(
        session, housing_service.create_application(session, org, body)
    )


@applications_router.get("", response_model=dict[str, Any])
def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    reviewer_user_id: uuid.UUID | None = Query(None),
    q: str | None = Query(None),
    pending_approvals: bool = Query(False),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = housing_service.list_applications(
        session,
        org,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        priority=priority,
        reviewer_user_id=reviewer_user_id,
        q=q,
        pending_approvals=pending_approvals,
    )
    return _page(
        [housing_service.application_out_dict(session, row) for row in rows],
        page,
        page_size,
        total,
    )


@applications_router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return housing_service.application_out_dict(
        session, housing_service.get_application(session, org, application_id)
    )


@applications_router.patch("/{application_id}", response_model=ApplicationOut)
def patch_application(
    application_id: uuid.UUID,
    body: ApplicationUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return housing_service.application_out_dict(
        session, housing_service.update_application(session, org, application_id, body)
    )


@applications_router.post("/{application_id}/submit", response_model=ApplicationOut)
def submit_application(
    application_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return housing_service.application_out_dict(
        session, housing_service.transition_application(session, org, application_id, "submitted")
    )


@applications_router.post("/{application_id}/request-information", response_model=ApplicationOut)
def request_information(
    application_id: uuid.UUID,
    body: InformationRequiredRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return housing_service.application_out_dict(
        session, housing_service.request_information(session, org, application_id, body)
    )


@applications_router.post("/{application_id}/decide", response_model=DecisionOut, status_code=201)
def decide_application(
    application_id: uuid.UUID,
    body: DecisionCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return housing_service.record_decision(session, org, application_id, body)


@applications_router.get("/{application_id}/history", response_model=list[ApplicationHistoryOut])
def application_history(
    application_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return housing_service.list_history(session, org, application_id)


@applications_router.get("/{application_id}/decisions", response_model=list[DecisionOut])
def application_decisions(
    application_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return housing_service.list_decisions(session, org, application_id)


@waiting_list_router.get("", response_model=dict[str, Any])
def list_waiting_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query("active", alias="status"),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = housing_service.list_waiting_list(
        session, org, page=page, page_size=page_size, status_filter=status_filter
    )
    return _page(
        [housing_service.waiting_list_out_dict(session, row) for row in rows],
        page,
        page_size,
        total,
    )


@waiting_list_router.post("", response_model=WaitingListOut, status_code=201)
def add_waiting_list(
    body: WaitingListAdd,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    entry = housing_service.add_to_waiting_list(session, org, body)
    return housing_service.waiting_list_out_dict(session, entry)


@waiting_list_router.patch("/{entry_id}", response_model=WaitingListOut)
def patch_waiting_list(
    entry_id: uuid.UUID,
    body: WaitingListUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    entry = housing_service.update_waiting_list_entry(session, org, entry_id, body)
    return housing_service.waiting_list_out_dict(session, entry)


router.include_router(applications_router)
router.include_router(waiting_list_router)
