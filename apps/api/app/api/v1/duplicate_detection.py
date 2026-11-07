"""F3.11 Duplicate detection API. Search-based; no AI per record; no auto merge/delete."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.duplicate_detection import service as dd_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/duplicate-detections", tags=["duplicate-detections"])


class RunDetectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_types: list[str] | None = None
    source_record_type: str | None = None
    source_record_id: UUID | None = None


class ReviewFindingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(confirm|dismiss|defer)$")
    review_comment: str | None = Field(default=None, max_length=2000)


@router.post("/runs")
def start_run(
    body: RunDetectionRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    trigger = "record" if body.source_record_id else "manual"
    result = dd_service.run_detection(
        session,
        org,
        record_types=body.record_types,
        source_record_type=body.source_record_type,
        source_record_id=body.source_record_id,
        trigger=trigger,
    )
    session.commit()
    return result


@router.get("/runs")
def list_runs(
    limit: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return dd_service.list_runs(session, org, limit=limit)


@router.get("/runs/{run_id}")
def get_run(
    run_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return dd_service.get_run(session, org, run_id)


@router.get("/findings")
def list_findings(
    review_status: str | None = None,
    record_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return dd_service.list_findings(
        session, org, review_status=review_status, record_type=record_type, limit=limit
    )


@router.get("/findings/{finding_id}")
def get_finding(
    finding_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return dd_service.get_finding(session, org, finding_id)


@router.post("/findings/{finding_id}/review")
def review_finding(
    finding_id: UUID,
    body: ReviewFindingRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = dd_service.review_finding(
        session,
        org,
        finding_id,
        decision=body.decision,
        review_comment=body.review_comment,
    )
    session.commit()
    return result
