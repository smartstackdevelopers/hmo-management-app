"""F3.7 support-plan draft API. Approval does not apply the draft."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.support_plan_drafts import service as draft_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/support-plan-drafts", tags=["support-plan-drafts"])


class GenerateDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: UUID
    plan_id: UUID | None = None
    force: bool = False


class EditDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: dict


class ReviewDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_comment: str | None = Field(default=None, max_length=2000)


@router.post("")
def generate(
    body: GenerateDraftRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = draft_service.generate_draft(
        session, org, tenant_id=body.tenant_id, plan_id=body.plan_id, force=body.force
    )
    session.commit()
    return result


@router.get("/tenants/{tenant_id}")
def list_for_tenant(
    tenant_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return draft_service.list_drafts(session, org, tenant_id)


@router.get("/{draft_id}")
def get_one(
    draft_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return draft_service.get_draft(session, org, draft_id)


@router.patch("/{draft_id}")
def edit(
    draft_id: UUID,
    body: EditDraftRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = draft_service.edit_draft(session, org, draft_id, body.content)
    session.commit()
    return result


@router.post("/{draft_id}/submit")
def submit(
    draft_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = draft_service.submit_draft(session, org, draft_id)
    session.commit()
    return result


@router.post("/{draft_id}/approve")
def approve(
    draft_id: UUID,
    body: ReviewDraftRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = draft_service.decide_draft(session, org, draft_id, decision="approve", review_comment=body.review_comment)
    session.commit()
    return result


@router.post("/{draft_id}/reject")
def reject(
    draft_id: UUID,
    body: ReviewDraftRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = draft_service.decide_draft(session, org, draft_id, decision="reject", review_comment=body.review_comment)
    session.commit()
    return result


@router.post("/{draft_id}/apply")
def apply(
    draft_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = draft_service.apply_draft(session, org, draft_id)
    session.commit()
    return result
