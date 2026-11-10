"""Tenant self profile, assigned housing, and scoped document upload."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.tenant_portal import documents as document_service
from app.tenant_portal import profile as profile_service
from app.tenant_portal.schemas import TenantHousingOut, TenantSelfOut, TenantSelfUpdate
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/tenant", tags=["tenant-self"])


@router.get("/me", response_model=TenantSelfOut)
def get_me(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> TenantSelfOut:
    return profile_service.get_own_profile(session, org)


@router.patch("/me", response_model=TenantSelfOut)
def patch_me(
    body: TenantSelfUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> TenantSelfOut:
    return profile_service.update_own_profile(session, org, body)


@router.get("/me/housing", response_model=TenantHousingOut)
def get_my_housing(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> TenantHousingOut:
    return profile_service.get_own_housing(session, org)


@router.post("/me/documents", status_code=201)
async def upload_my_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    data = await file.read()
    return document_service.upload_own_document(
        session,
        org,
        title=title,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
    )
