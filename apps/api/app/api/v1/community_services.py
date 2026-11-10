"""Published community services for the caller's organisation."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.tenant_portal import catalogue
from app.tenant_portal.schemas import CommunityServiceOut, CommunityServiceUpdate, CommunityServiceWrite
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/community-services", tags=["community-services"])


@router.get("", response_model=dict[str, list[CommunityServiceOut]])
def list_community_services(
    q: str | None = Query(None, max_length=255),
    category: str | None = Query(None, max_length=32),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, list[CommunityServiceOut]]:
    return {"items": catalogue.list_community_services(session, org, q=q, category=category)}


@router.post("", response_model=CommunityServiceOut, status_code=201)
def create_community_service(
    body: CommunityServiceWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServiceOut:
    return catalogue.create_community_service(session, org, body)


@router.patch("/{service_id}", response_model=CommunityServiceOut)
def patch_community_service(
    service_id: uuid.UUID,
    body: CommunityServiceUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> CommunityServiceOut:
    return catalogue.update_community_service(session, org, service_id, body)
