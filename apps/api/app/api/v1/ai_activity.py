"""F3.14 AI activity logs, sources/confidence, and wrong-answer feedback APIs."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.ai_transparency import service as tx_service
from app.ai_transparency.constants import FEEDBACK_CATEGORIES
from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/ai-activity", tags=["ai-activity"])


class FeedbackSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(..., min_length=1, max_length=64)
    explanation: str | None = Field(default=None, max_length=2000)


class FeedbackReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(pattern="^(start_review|assign|resolve|reject)$")
    resolution_notes: str | None = Field(default=None, max_length=2000)
    rejection_reason: str | None = Field(default=None, max_length=2000)
    assigned_reviewer_id: UUID | None = None


@router.get("")
def list_activities(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    feature_id: str | None = Query(None, max_length=100),
    execution_status: str | None = Query(None, max_length=32),
    sources_only: bool | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return tx_service.list_activities(
        session,
        org,
        limit=limit,
        offset=offset,
        feature_id=feature_id,
        execution_status=execution_status,
        sources_only=sources_only,
    )


@router.get("/categories")
def feedback_categories(
    org: OrganisationContext = Depends(get_organisation_context),
) -> dict:
    _ = org
    return {
        "categories": sorted(FEEDBACK_CATEGORIES),
        "confidence_note": (
            "Confidence values are never fabricated. "
            "When no reliable signal exists, the UI shows Confidence unavailable."
        ),
    }


@router.get("/feedback")
def list_feedback(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    review_status: str | None = Query(None, max_length=32),
    category: str | None = Query(None, max_length=64),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return tx_service.list_feedback(
        session,
        org,
        limit=limit,
        offset=offset,
        review_status=review_status,
        category=category,
    )


@router.get("/feedback/stats")
def feedback_stats(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return tx_service.feedback_stats(session, org)


@router.get("/feedback/{feedback_id}")
def get_feedback(
    feedback_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return tx_service.get_feedback(session, org, feedback_id)


@router.post("/feedback/{feedback_id}/review")
def review_feedback(
    feedback_id: UUID,
    body: FeedbackReviewRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = tx_service.review_feedback(
        session,
        org,
        feedback_id,
        action=body.action,
        resolution_notes=body.resolution_notes,
        rejection_reason=body.rejection_reason,
        assigned_reviewer_id=body.assigned_reviewer_id,
    )
    session.commit()
    return result


@router.get("/{activity_id}")
def get_activity(
    activity_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = tx_service.get_activity(session, org, activity_id, audit_source_access=True)
    session.commit()
    return result


@router.post("/{activity_id}/feedback")
def submit_feedback(
    activity_id: UUID,
    body: FeedbackSubmitRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = tx_service.submit_feedback(
        session,
        org,
        activity_id=activity_id,
        category=body.category,
        explanation=body.explanation,
    )
    session.commit()
    return result
