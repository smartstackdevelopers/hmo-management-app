"""Published job and training listings for the caller's organisation."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.tenant_portal import catalogue
from app.tenant_portal.schemas import OpportunityOut, OpportunityUpdate, OpportunityWrite
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=dict[str, list[OpportunityOut]])
def list_opportunities(
    kind: str | None = Query(None, max_length=32),
    q: str | None = Query(None, max_length=255),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, list[OpportunityOut]]:
    return {"items": catalogue.list_opportunities(session, org, kind=kind, q=q)}


@router.post("", response_model=OpportunityOut, status_code=201)
def create_opportunity(
    body: OpportunityWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> OpportunityOut:
    return catalogue.create_opportunity(session, org, body)


@router.patch("/{listing_id}", response_model=OpportunityOut)
def patch_opportunity(
    listing_id: uuid.UUID,
    body: OpportunityUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> OpportunityOut:
    return catalogue.update_opportunity(session, org, listing_id, body)
