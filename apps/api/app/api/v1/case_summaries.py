"""F3.5 case summary API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.case_summaries import service as case_service
from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/case-summaries", tags=["case-summaries"])


class GenerateCaseSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: UUID
    force: bool = False


class ReviewCaseSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(approve|reject)$")
    review_comment: str | None = Field(default=None, max_length=2000)


@router.post("")
def generate(
    body: GenerateCaseSummaryRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = case_service.generate_summary(session, org, tenant_id=body.tenant_id, force=body.force)
    session.commit()
    return result


@router.get("/tenants/{tenant_id}/versions")
def versions(
    tenant_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return case_service.list_versions(session, org, tenant_id, page=page, page_size=page_size)


@router.get("/{summary_id}")
def get_one(
    summary_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return case_service.get_summary(session, org, summary_id)


@router.get("/{summary_id}/sources")
def sources(
    summary_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    summary = case_service.get_summary(session, org, summary_id)
    return {"summary_id": summary["id"], "version_number": summary["version_number"], "source_refs": summary["source_refs"], "stale": summary["stale"]}


@router.post("/{summary_id}/regenerate")
def regenerate(
    summary_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = case_service.regenerate_summary(session, org, summary_id)
    session.commit()
    return result


@router.post("/{summary_id}/review")
def review(
    summary_id: UUID,
    body: ReviewCaseSummaryRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = case_service.review_summary(
        session,
        org,
        summary_id,
        decision=body.decision,
        review_comment=body.review_comment,
    )
    session.commit()
    return result
