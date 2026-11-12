"""F6.7 Council Portal API — add-on officers outside core HMoreRole."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.council_portal import service as portal_service
from app.council_portal.access import get_council_officer_context
from app.council_portal.context import CouncilPortalContext
from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/council-portal", tags=["council-portal"])


class OfficerInviteBody(BaseModel):
    user_id: uuid.UUID
    display_name: str | None = None
    council_organisation_name: str | None = None
    notes: str | None = None


class OfficerStatusBody(BaseModel):
    status: str = Field(pattern="^(active|suspended|revoked)$")


class ShareCreateBody(BaseModel):
    application_id: uuid.UUID
    purpose: str = Field(min_length=1, max_length=2000)
    include_evidence: bool = False
    include_approval_history: bool = True
    scopes: list[str] | None = None
    expires_at: datetime | None = None
    evidence_pack_id: uuid.UUID | None = None


@router.get("/admin/dashboard")
def admin_dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return portal_service.admin_dashboard(session, org)


@router.get("/admin/officers")
def admin_list_officers(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": portal_service.list_officers(session, org)}


@router.post("/admin/officers")
def admin_invite_officer(
    body: OfficerInviteBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return portal_service.invite_officer(session, org, **body.model_dump())


@router.patch("/admin/officers/{officer_id}/status")
def admin_officer_status(
    officer_id: uuid.UUID,
    body: OfficerStatusBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return portal_service.set_officer_status(session, org, officer_id, body.status)


@router.get("/admin/shares")
def admin_list_shares(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": portal_service.list_shares(session, org)}


@router.post("/admin/shares")
def admin_create_share(
    body: ShareCreateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return portal_service.create_share(session, org, **body.model_dump())


@router.post("/admin/shares/{share_id}/revoke")
def admin_revoke_share(
    share_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return portal_service.revoke_share(session, org, share_id)


@router.get("/officer/inbox")
def officer_inbox(
    cctx: CouncilPortalContext = Depends(get_council_officer_context),
    session: Session = Depends(get_session),
) -> dict:
    return portal_service.officer_inbox(session, cctx)


@router.get("/officer/shares/{share_id}")
def officer_share_detail(
    share_id: uuid.UUID,
    cctx: CouncilPortalContext = Depends(get_council_officer_context),
    session: Session = Depends(get_session),
) -> dict:
    return portal_service.officer_get_application(session, cctx, share_id)


@router.get("/officer/reports/summary")
def officer_reports(
    cctx: CouncilPortalContext = Depends(get_council_officer_context),
    session: Session = Depends(get_session),
) -> dict:
    return portal_service.officer_report_summary(session, cctx)
