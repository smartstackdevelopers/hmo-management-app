"""Help Near Me postcode search and outdated listing reports (F5.2)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.help_near_me import service as help_near_me
from app.help_near_me.schemas import (
    ManualCoordinatesBody,
    NearbySearchOut,
    OutdatedReportAdminUpdate,
    OutdatedReportOut,
    OutdatedReportPage,
    OutdatedReportWrite,
    PostcodeValidateOut,
    ServiceGeocodeOut,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/help-near-me", tags=["help-near-me"])


@router.get("/validate-postcode", response_model=PostcodeValidateOut)
def validate_postcode(
    postcode: str = Query(..., min_length=2, max_length=16),
    org: OrganisationContext = Depends(get_organisation_context),
) -> PostcodeValidateOut:
    return help_near_me.validate_postcode(org, postcode)


@router.get("/nearby", response_model=NearbySearchOut)
def search_nearby(
    postcode: str = Query(..., min_length=2, max_length=16),
    category: str | None = Query(None, max_length=32),
    radius_km: float | None = Query(None, ge=0.5, le=100),
    sort: str = Query("distance", max_length=16),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> NearbySearchOut:
    return help_near_me.search_nearby(
        session,
        org,
        postcode=postcode,
        category=category,
        radius_km=radius_km,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.post("/reports", response_model=OutdatedReportOut, status_code=201)
def submit_report(
    body: OutdatedReportWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> OutdatedReportOut:
    return help_near_me.submit_outdated_report(session, org, body)


@router.get("/reports/mine", response_model=OutdatedReportPage)
def list_my_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> OutdatedReportPage:
    return help_near_me.list_own_reports(session, org, page=page, page_size=page_size)


@router.get("/reports/admin", response_model=OutdatedReportPage)
def list_admin_reports(
    status: str | None = Query(None, max_length=32),
    category: str | None = Query(None, max_length=32),
    q: str | None = Query(None, max_length=255),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> OutdatedReportPage:
    return help_near_me.list_admin_reports(
        session,
        org,
        status_filter=status,
        category=category,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/reports/admin/{report_id}", response_model=OutdatedReportOut)
def get_admin_report(
    report_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> OutdatedReportOut:
    return help_near_me.get_admin_report(session, org, report_id)


@router.patch("/reports/admin/{report_id}", response_model=OutdatedReportOut)
def patch_admin_report(
    report_id: uuid.UUID,
    body: OutdatedReportAdminUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> OutdatedReportOut:
    return help_near_me.update_admin_report(session, org, report_id, body)


@router.post("/services/{service_id}/geocode", response_model=ServiceGeocodeOut)
def geocode_service(
    service_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> ServiceGeocodeOut:
    return help_near_me.geocode_service_from_address(session, org, service_id)


@router.put("/services/{service_id}/coordinates", response_model=ServiceGeocodeOut)
def set_service_coordinates(
    service_id: uuid.UUID,
    body: ManualCoordinatesBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> ServiceGeocodeOut:
    return help_near_me.set_manual_coordinates(session, org, service_id, body)
