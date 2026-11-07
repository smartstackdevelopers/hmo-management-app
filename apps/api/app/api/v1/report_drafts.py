"""F3.13 report drafts API. No auto-distribution."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.report_drafts import service as draft_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/report-drafts", tags=["report-drafts"])


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_type: str = Field(pattern="^(weekly|monthly)$")
    regenerate: bool = False


class EditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edited_body: str = Field(min_length=1, max_length=20000)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(approve|reject)$")
    review_comment: str | None = Field(default=None, max_length=2000)


@router.post("")
def generate(
    body: GenerateRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = draft_service.generate_draft(
        session, org, period_type=body.period_type, regenerate=body.regenerate
    )
    session.commit()
    return result


@router.get("")
def list_items(
    limit: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return draft_service.list_drafts(session, org, limit=limit)


@router.get("/{draft_id}")
def get_item(
    draft_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return draft_service.get_draft(session, org, draft_id)


@router.patch("/{draft_id}")
def edit_item(
    draft_id: UUID,
    body: EditRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = draft_service.edit_draft(session, org, draft_id, edited_body=body.edited_body)
    session.commit()
    return result


@router.post("/{draft_id}/review")
def review_item(
    draft_id: UUID,
    body: ReviewRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = draft_service.review_draft(
        session, org, draft_id, decision=body.decision, review_comment=body.review_comment
    )
    session.commit()
    return result
