"""F3.8 housing application analysis API. Never records a housing decision."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.housing_application_analysis import service as analysis_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/housing-application-analyses", tags=["housing-application-analyses"])


class RunAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: UUID
    force: bool = False


class FindingDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(confirm|dismiss)$")
    review_comment: str | None = Field(default=None, max_length=2000)


class ReviewAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_comment: str | None = Field(default=None, max_length=2000)


@router.post("")
def run_analysis(
    body: RunAnalysisRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = analysis_service.run_analysis(session, org, application_id=body.application_id, force=body.force)
    session.commit()
    return result


@router.get("/applications/{application_id}")
def list_for_application(
    application_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return analysis_service.list_analyses(session, org, application_id)


@router.get("/{analysis_id}")
def get_one(
    analysis_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return analysis_service.get_analysis(session, org, analysis_id)


@router.post("/{analysis_id}/review")
def review(
    analysis_id: UUID,
    body: ReviewAnalysisRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = analysis_service.review_analysis(session, org, analysis_id, review_comment=body.review_comment)
    session.commit()
    return result


@router.post("/findings/{finding_id}/decide")
def decide(
    finding_id: UUID,
    body: FindingDecisionRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = analysis_service.decide_finding(
        session,
        org,
        finding_id,
        decision=body.decision,
        review_comment=body.review_comment,
    )
    session.commit()
    return result
