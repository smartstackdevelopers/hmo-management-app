"""Tenant employment preparation APIs (F5.3)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.employment import service as employment
from app.employment.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    AssessmentUpdate,
    CareerGoalWrite,
    CvAssistRequest,
    CvCreate,
    CvUpdate,
    InterviewNoteWrite,
    StaffSupportNotesWrite,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/employment", tags=["employment"])


@router.get("/skill-categories")
def skill_categories(
    org: OrganisationContext = Depends(get_organisation_context),
) -> dict:
    _ = org
    return employment.list_skill_categories()


@router.get("/assessment")
def get_assessment(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.get_or_create_assessment(session, org)


@router.put("/assessment")
def put_assessment(
    body: AssessmentUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.update_assessment(session, org, body)


@router.get("/cvs")
def get_cvs(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.list_cvs(session, org)


@router.post("/cvs", status_code=201)
def post_cv(
    body: CvCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.create_cv(session, org, body)


@router.get("/cvs/{cv_id}")
def get_cv(
    cv_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.get_cv(session, org, cv_id)


@router.patch("/cvs/{cv_id}")
def patch_cv(
    cv_id: uuid.UUID,
    body: CvUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.update_cv(session, org, cv_id, body)


@router.post("/cvs/{cv_id}/duplicate", status_code=201)
def post_duplicate_cv(
    cv_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.duplicate_cv(session, org, cv_id)


@router.delete("/cvs/{cv_id}")
def delete_cv(
    cv_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.delete_cv(session, org, cv_id)


@router.post("/cvs/{cv_id}/pdf")
def post_cv_pdf(
    cv_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.generate_cv_pdf(session, org, cv_id)


@router.get("/cvs/{cv_id}/pdf")
def get_cv_pdf(
    cv_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    return employment.download_cv_pdf(session, org, cv_id)


@router.post("/cvs/assist")
def post_cv_assist(
    body: CvAssistRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.assist_cv_wording(session, org, body)


@router.get("/applications/dashboard")
def get_application_dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.application_dashboard(session, org)


@router.get("/applications")
def get_applications(
    status: str | None = Query(None),
    q: str | None = Query(None),
    archived: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.list_applications(
        session, org, status_filter=status, q=q, archived=archived, page=page, page_size=page_size
    )


@router.post("/applications", status_code=201)
def post_application(
    body: ApplicationCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.create_application(session, org, body)


@router.patch("/applications/{application_id}")
def patch_application(
    application_id: uuid.UUID,
    body: ApplicationUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.update_application(session, org, application_id, body)


@router.delete("/applications/{application_id}")
def delete_application(
    application_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.delete_application(session, org, application_id)


@router.get("/roadmap")
def get_roadmap(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.get_roadmap(session, org)


@router.get("/career-goals")
def get_career_goals(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.list_career_goals(session, org)


@router.post("/career-goals", status_code=201)
def post_career_goal(
    body: CareerGoalWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.create_career_goal(session, org, body)


@router.put("/career-goals/{goal_id}")
def put_career_goal(
    goal_id: uuid.UUID,
    body: CareerGoalWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.update_career_goal(session, org, goal_id, body)


@router.get("/interview-prep")
def get_interview_prep(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.list_interview_notes(session, org)


@router.post("/interview-prep", status_code=201)
def post_interview_prep(
    body: InterviewNoteWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.upsert_interview_note(session, org, body)


@router.get("/staff/tenants/{tenant_id}/summary")
def staff_summary(
    tenant_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.staff_employment_summary(session, org, tenant_id)


@router.put("/staff/tenants/{tenant_id}/support-notes")
def staff_support_notes(
    tenant_id: uuid.UUID,
    body: StaffSupportNotesWrite,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
):
    return employment.update_staff_support_notes(session, org, tenant_id, body.notes)
