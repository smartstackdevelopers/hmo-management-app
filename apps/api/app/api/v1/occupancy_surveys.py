"""Occupancy site-survey API (F1.10). No camera capture or occupancy detection."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.occupancy import service as survey_service
from app.occupancy.schemas import FindingCreate, FindingUpdate, RoomAssessmentIn, SurveyCreate, SurveyUpdate
from app.rbac.context import AuthorizationContext
from app.rbac.deps import get_authorization_context
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/occupancy-surveys", tags=["occupancy-surveys"])


@router.post("", status_code=201)
def create_survey(
    body: SurveyCreate,
    _authz: AuthorizationContext = Depends(get_authorization_context),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return survey_service.create_survey(session, org, body)


@router.get("")
def list_surveys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    property_id: uuid.UUID | None = None,
    _authz: AuthorizationContext = Depends(get_authorization_context),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items, total = survey_service.list_surveys(
        session, org, page=page, page_size=page_size, property_id=property_id
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/{survey_id}")
def get_survey(
    survey_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(get_authorization_context),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    row = survey_service.get_survey(session, org, survey_id)
    return survey_service._public_survey(row)


@router.patch("/{survey_id}")
def patch_survey(
    survey_id: uuid.UUID,
    body: SurveyUpdate,
    _authz: AuthorizationContext = Depends(get_authorization_context),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return survey_service.update_survey(session, org, survey_id, body)


@router.post("/{survey_id}/room-assessments", status_code=201)
def add_room_assessment(
    survey_id: uuid.UUID,
    body: RoomAssessmentIn,
    _authz: AuthorizationContext = Depends(get_authorization_context),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return survey_service.upsert_room_assessment(session, org, survey_id, body)


@router.get("/{survey_id}/room-assessments")
def list_room_assessments(
    survey_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(get_authorization_context),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return {"items": survey_service.list_room_assessments(session, org, survey_id)}


@router.post("/{survey_id}/findings", status_code=201)
def create_finding(
    survey_id: uuid.UUID,
    body: FindingCreate,
    _authz: AuthorizationContext = Depends(get_authorization_context),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return survey_service.add_finding(session, org, survey_id, body)


@router.get("/{survey_id}/findings")
def list_findings(
    survey_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(get_authorization_context),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return {"items": survey_service.list_findings(session, org, survey_id)}


@router.patch("/findings/{finding_id}")
def patch_finding(
    finding_id: uuid.UUID,
    body: FindingUpdate,
    _authz: AuthorizationContext = Depends(get_authorization_context),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return survey_service.update_finding(session, org, finding_id, body)
