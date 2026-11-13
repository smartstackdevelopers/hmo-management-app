"""F8.4 optional LMS API."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.lms import LmsCategory, LmsCertificate, LmsCourse
from app.db.session import get_session
from app.lms import access, service
from app.lms.certificates import build_certificate_pdf
from app.lms.service import _settings
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/lms", tags=["lms"])


class SettingsBody(BaseModel):
    enabled: bool | None = None
    privacy_review_complete: bool | None = None
    default_certificate_validity_days: int | None = Field(default=None, ge=1, le=3650)
    tenant_courses_enabled: bool | None = None
    reminder_config: dict[str, Any] | None = None


class CourseBody(BaseModel):
    category_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    instructor: str | None = None
    learning_objectives: list[str] | None = None
    duration_minutes: int | None = None
    difficulty: str | None = None
    certificate_eligible: bool = True
    pass_mark_percent: int = Field(default=80, ge=1, le=100)
    certificate_validity_days: int | None = None
    staff_only: bool = True
    tenant_visible: bool = False


class AssignBody(BaseModel):
    course_id: uuid.UUID
    target_type: str
    target_value: str
    mandatory: bool = False
    due_date: date | None = None


class LessonCompleteBody(BaseModel):
    enrollment_id: uuid.UUID
    lesson_id: uuid.UUID


class AssessmentBody(BaseModel):
    quiz_id: uuid.UUID
    enrollment_id: uuid.UUID
    answers: list[dict[str, Any]]


class ManualMarkBody(BaseModel):
    passed: bool
    feedback: str | None = None


@router.get("/settings")
def get_settings_api(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.LMS_READ)
    return service.settings_dict(_settings(session, ctx.organisation_id))


@router.patch("/settings")
def patch_settings(body: SettingsBody, session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.LMS_MANAGE)
    return service.update_settings(session, ctx, body.model_dump(exclude_unset=True))


@router.get("/categories")
def list_categories(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.LMS_READ)
    service.ensure_categories(session, ctx.organisation_id)
    rows = session.scalars(select(LmsCategory).where(LmsCategory.organisation_id == ctx.organisation_id).order_by(LmsCategory.sort_order))
    return [{"id": str(r.id), "slug": r.slug, "name": r.name, "active": r.active} for r in rows]


@router.get("/admin/dashboard")
def admin_dashboard(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    return service.admin_dashboard(session, ctx)


@router.get("/learn/dashboard")
def learn_dashboard(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    return service.learner_dashboard(session, ctx)


@router.get("/learn/courses")
def learn_courses(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> list[dict[str, Any]]:
    return service.list_learner_courses(session, ctx)


@router.post("/courses")
def create_course(body: CourseBody, session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    course = service.create_course(session, ctx, body.model_dump())
    return service.course_to_dict(course)


@router.get("/courses")
def list_courses(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context), status: str | None = None) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.LMS_READ)
    q = select(LmsCourse).where(LmsCourse.organisation_id == ctx.organisation_id)
    if status:
        q = q.where(LmsCourse.status == status)
    return [service.course_to_dict(c) for c in session.scalars(q).all()]


@router.post("/courses/{course_id}/publish")
def publish_course(course_id: uuid.UUID, session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    return service.course_to_dict(service.publish_course(session, ctx, course_id))


@router.post("/assignments")
def create_assignment(body: AssignBody, session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    a = service.assign_course(
        session,
        ctx,
        course_id=body.course_id,
        target_type=body.target_type,
        target_value=body.target_value,
        mandatory=body.mandatory,
        due_date=body.due_date,
    )
    return {"id": str(a.id)}


@router.post("/lessons/complete")
def complete_lesson(body: LessonCompleteBody, session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, str]:
    service.complete_lesson(session, ctx, body.enrollment_id, body.lesson_id)
    return {"status": "ok"}


@router.post("/assessments/submit")
def submit_assessment(body: AssessmentBody, session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    attempt = service.submit_assessment(session, ctx, quiz_id=body.quiz_id, enrollment_id=body.enrollment_id, answers=body.answers)
    return {"id": str(attempt.id), "status": attempt.status, "passed": attempt.passed, "score_percent": attempt.score_percent}


@router.post("/assessments/{attempt_id}/mark")
def mark_assessment(attempt_id: uuid.UUID, body: ManualMarkBody, session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    attempt = service.manual_mark_attempt(session, ctx, attempt_id, passed=body.passed, feedback=body.feedback)
    return {"id": str(attempt.id), "passed": attempt.passed}


@router.get("/certificates/verify")
def verify_cert(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context), ref: str = Query(...)) -> dict[str, Any]:
    return service.verify_certificate(session, ctx.organisation_id, ref)


@router.get("/certificates/{certificate_id}/pdf")
def cert_pdf(certificate_id: uuid.UUID, session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> Response:
    access.require_learn(ctx)
    cert = session.get(LmsCertificate, certificate_id)
    if cert is None or cert.organisation_id != ctx.organisation_id:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    return Response(content=build_certificate_pdf(cert), media_type="application/pdf")
