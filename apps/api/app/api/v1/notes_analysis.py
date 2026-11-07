"""F3.4 Notes Analysis API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.notes_analysis import service as na_service
from app.notes_analysis.schemas import (
    AnalyseNoteRequest,
    AnalysisReviewRequest,
    BatchEligibleRequest,
    SuggestionDecisionRequest,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/notes-analysis", tags=["notes-analysis"])


@router.post("/analyse")
def analyse_note(
    body: AnalyseNoteRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = na_service.run_analysis(
        session,
        org,
        daily_log_id=body.daily_log_id,
        force=body.force,
        generation_kind="on_demand",
    )
    session.commit()
    return result


@router.get("/analyses/{analysis_id}")
def get_analysis(
    analysis_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return na_service.get_analysis(session, org, analysis_id)


@router.get("/inbox")
def inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return na_service.list_inbox(session, org, page=page, page_size=page_size)


@router.post("/suggestions/{suggestion_id}/decide")
def decide_suggestion(
    suggestion_id: UUID,
    body: SuggestionDecisionRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = na_service.decide_suggestion(
        session,
        org,
        suggestion_id,
        decision=body.decision,
        reviewer_note=body.reviewer_note,
        edited_body=body.edited_body,
    )
    session.commit()
    return result


@router.post("/analyses/{analysis_id}/review")
def review_analysis(
    analysis_id: UUID,
    body: AnalysisReviewRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = na_service.review_analysis(
        session,
        org,
        analysis_id,
        decision=body.decision,
        review_comment=body.review_comment,
    )
    session.commit()
    return result


@router.get("/batch/eligible")
def batch_eligible(
    limit: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return na_service.list_eligible_for_batch(session, org, limit=limit)


@router.post("/batch/run")
def batch_run(
    body: BatchEligibleRequest | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    limit = body.limit if body else 50
    result = na_service.run_batch_for_org(session, org, limit=limit)
    session.commit()
    return result
