"""Tenant job matching APIs (F5.4)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.job_matching import service as job_matching
from app.job_matching.schemas import (
    AddToTrackerRequest,
    MatchExplainRequest,
    PreferencesUpdate,
    StructuredJobImportBatch,
    StructuredTrainingImport,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/job-matching", tags=["job-matching"])


@router.get("/sources")
def get_sources(
    org: OrganisationContext = Depends(get_organisation_context),
):
    return job_matching.list_sources()


@router.get("/profile")
def get_profile(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.get_matching_profile(session, org)


@router.get("/preferences")
def get_preferences(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.get_preferences(session, org)


@router.put("/preferences")
def put_preferences(
    body: PreferencesUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.update_preferences(session, org, body)


@router.get("/jobs/search")
def search_jobs(
    q: str | None = None,
    employer: str | None = None,
    location: str | None = None,
    employment_type: str | None = None,
    skills: str | None = None,
    sort: str = Query(default="relevance"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    refresh_live: bool = Query(default=True),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.search_jobs(
        session,
        org,
        q=q,
        employer=employer,
        location=location,
        employment_type=employment_type,
        skills=skills,
        sort=sort,
        page=page,
        page_size=page_size,
        refresh_live=refresh_live,
    )


@router.get("/jobs/recommended")
def recommended_jobs(
    limit: int = Query(default=20, ge=1, le=50),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.recommend_jobs(session, org, limit=limit)


@router.get("/jobs/{job_id}")
def get_job(
    job_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.get_job(session, org, job_id)


@router.post("/jobs/import")
def import_jobs(
    body: StructuredJobImportBatch,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.import_structured_jobs(session, org, body)


@router.get("/saved-jobs")
def saved_jobs(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.list_saved_jobs(session, org)


@router.post("/saved-jobs/{job_id}")
def save_job(
    job_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.save_job(session, org, job_id)


@router.delete("/saved-jobs/{job_id}")
def unsave_job(
    job_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.unsave_job(session, org, job_id)


@router.get("/training")
def training(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.recommend_training(session, org)


@router.post("/training/import")
def import_training(
    body: StructuredTrainingImport,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.import_structured_training(session, org, body)


@router.post("/training/{training_id}/save")
def save_training(
    training_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.save_training(session, org, training_id)


@router.put("/training/{training_id}/status")
def training_status(
    training_id: uuid.UUID,
    status: str = Query(...),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.mark_training_status(session, org, training_id, status)


@router.post("/tracker")
def add_to_tracker(
    body: AddToTrackerRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.add_job_to_tracker(session, org, body)


@router.post("/explain")
def explain(
    body: MatchExplainRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.explain_match(session, org, body)


@router.get("/staff/tenants/{tenant_id}/progress")
def staff_progress(
    tenant_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return job_matching.staff_match_progress(session, org, tenant_id)
