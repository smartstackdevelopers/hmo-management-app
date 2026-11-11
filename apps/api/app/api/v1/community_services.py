"""Community directory listings for the caller's organisation (F4.1 / F5.1)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.tenant_portal import catalogue
from app.tenant_portal.schemas import (
    CommunityServiceAdminOut,
    CommunityServiceAdminPage,
    CommunityServiceDeactivateBody,
    CommunityServiceFlagBody,
    CommunityServiceOut,
    CommunityServicePage,
    CommunityServiceUpdate,
    CommunityServiceVerifyBody,
    CommunityServiceWrite,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/community-services", tags=["community-services"])


@router.get("/categories")
def get_service_categories(
    org: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, list[dict[str, str]]]:
    return catalogue.list_service_categories(org)


@router.get("/admin", response_model=CommunityServiceAdminPage)
def list_admin_community_services(
    q: str | None = Query(None, max_length=255),
    category: str | None = Query(None, max_length=32),
    verification_status: str | None = Query(None, max_length=32),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServiceAdminPage:
    return catalogue.list_admin_community_services(
        session,
        org,
        q=q,
        category=category,
        verification_status=verification_status,
        page=page,
        page_size=page_size,
    )


@router.get("", response_model=CommunityServicePage)
def list_community_services(
    q: str | None = Query(None, max_length=255),
    category: str | None = Query(None, max_length=32),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    has_opening_hours: bool | None = Query(None),
    has_eligibility: bool | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServicePage:
    return catalogue.list_community_services(
        session,
        org,
        q=q,
        category=category,
        page=page,
        page_size=page_size,
        has_opening_hours=has_opening_hours,
        has_eligibility=has_eligibility,
    )


@router.post("", response_model=CommunityServiceAdminOut, status_code=201)
def create_community_service(
    body: CommunityServiceWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServiceAdminOut:
    return catalogue.create_community_service(session, org, body)


@router.get("/{service_id}", response_model=CommunityServiceOut)
def get_community_service(
    service_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServiceOut:
    return catalogue.get_community_service(session, org, service_id, admin=False)


@router.get("/{service_id}/admin", response_model=CommunityServiceAdminOut)
def get_admin_community_service(
    service_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServiceAdminOut:
    return catalogue.get_community_service(session, org, service_id, admin=True)


@router.patch("/{service_id}", response_model=CommunityServiceAdminOut)
def patch_community_service(
    service_id: uuid.UUID,
    body: CommunityServiceUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServiceAdminOut:
    return catalogue.update_community_service(session, org, service_id, body)


@router.post("/{service_id}/verify", response_model=CommunityServiceAdminOut)
def verify_community_service(
    service_id: uuid.UUID,
    body: CommunityServiceVerifyBody | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServiceAdminOut:
    return catalogue.verify_community_service(
        session,
        org,
        service_id,
        body or CommunityServiceVerifyBody(),
    )


@router.post("/{service_id}/flag-outdated", response_model=CommunityServiceAdminOut)
def flag_outdated_community_service(
    service_id: uuid.UUID,
    body: CommunityServiceFlagBody | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServiceAdminOut:
    return catalogue.flag_outdated_community_service(
        session,
        org,
        service_id,
        body or CommunityServiceFlagBody(),
    )


@router.post("/{service_id}/deactivate", response_model=CommunityServiceAdminOut)
def deactivate_community_service(
    service_id: uuid.UUID,
    body: CommunityServiceDeactivateBody | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServiceAdminOut:
    return catalogue.deactivate_community_service(
        session,
        org,
        service_id,
        body or CommunityServiceDeactivateBody(),
    )


@router.get("/{service_id}/verification-history")
def get_verification_history(
    service_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return catalogue.list_verification_history(session, org, service_id)
