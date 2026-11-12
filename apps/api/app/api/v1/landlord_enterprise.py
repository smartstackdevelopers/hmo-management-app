"""F6.1 Landlord Enterprise Tools API."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.landlord_enterprise import service as landlord
from app.landlord_enterprise.schemas import InspectionWrite, RentRecordStatusWrite, RentRecordWrite
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/landlord-enterprise", tags=["landlord-enterprise"])


@router.get("/dashboard")
def get_dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.enterprise_dashboard(session, org)


@router.get("/portfolio")
def get_portfolio(
    property_id: uuid.UUID | None = None,
    building: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    tenancy_status: str | None = None,
    inspection_status: str | None = None,
    repair_status: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.portfolio_analytics(
        session,
        org,
        property_id=property_id,
        building=building,
        date_from=date_from,
        date_to=date_to,
        tenancy_status=tenancy_status,
        inspection_status=inspection_status,
        repair_status=repair_status,
    )


@router.get("/rent-records")
def get_rent_records(
    property_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.list_rent_records(
        session,
        org,
        property_id=property_id,
        tenant_id=tenant_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.post("/rent-records", status_code=201)
def post_rent_record(
    body: RentRecordWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.create_rent_record(session, org, body)


@router.get("/rent-records/{rent_id}")
def get_rent_record(
    rent_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.get_rent_record(session, org, rent_id)


@router.post("/rent-records/{rent_id}/status")
def post_rent_status(
    rent_id: uuid.UUID,
    body: RentRecordStatusWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.update_rent_status(session, org, rent_id, body)


@router.delete("/rent-records/{rent_id}")
def delete_rent_record(
    rent_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.archive_rent_record(session, org, rent_id)


@router.get("/inspections")
def get_inspections(
    property_id: uuid.UUID | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.list_inspections(
        session,
        org,
        property_id=property_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.post("/inspections", status_code=201)
def post_inspection(
    body: InspectionWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.create_inspection(session, org, body)


@router.get("/inspections/{inspection_id}")
def get_inspection(
    inspection_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.get_inspection(session, org, inspection_id)


@router.put("/inspections/{inspection_id}")
def put_inspection(
    inspection_id: uuid.UUID,
    body: InspectionWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.update_inspection(session, org, inspection_id, body)


@router.get("/repairs")
def get_repairs(
    property_id: uuid.UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    overdue_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return landlord.list_repair_oversight(
        session,
        org,
        property_id=property_id,
        status=status,
        priority=priority,
        overdue_only=overdue_only,
        page=page,
        page_size=page_size,
    )
