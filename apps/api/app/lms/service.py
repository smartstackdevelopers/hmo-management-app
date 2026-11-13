"""F8.4 LMS orchestration."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.enums import HMoreRole
from app.db.models.lms import (
    LmsAssessmentAnswer,
    LmsAssessmentAttempt,
    LmsCategory,
    LmsCertificate,
    LmsCourse,
    LmsCourseAssignment,
    LmsCourseModule,
    LmsEnrollment,
    LmsLesson,
    LmsLessonCompletion,
    LmsQuestion,
    LmsQuiz,
    OrganisationLmsSettings,
)
from app.db.models.user import User
from app.lms import access, assessments, certificates
from app.lms.constants import ADDON_DISCLAIMER, DEFAULT_CATEGORIES
from app.ops.notifications import ReminderMessage, get_notification_provider
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _settings(session: Session, org_id: UUID) -> OrganisationLmsSettings:
    row = session.scalars(select(OrganisationLmsSettings).where(OrganisationLmsSettings.organisation_id == org_id)).first()
    if row is None:
        row = OrganisationLmsSettings(organisation_id=org_id)
        session.add(row)
        session.flush()
    return row


def assert_addon(session: Session, settings: Settings, org_id: UUID) -> OrganisationLmsSettings:
    if not settings.lms_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="LMS add-on is not enabled platform-wide")
    row = _settings(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="LMS disabled for organisation")
    return row


def settings_dict(row: OrganisationLmsSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "default_certificate_validity_days": row.default_certificate_validity_days,
        "tenant_courses_enabled": row.tenant_courses_enabled,
        "reminder_config": row.reminder_config,
        "disclaimer": ADDON_DISCLAIMER,
    }


def ensure_categories(session: Session, org_id: UUID) -> None:
    if session.scalar(select(func.count()).select_from(LmsCategory).where(LmsCategory.organisation_id == org_id)):
        return
    for idx, (slug, name) in enumerate(DEFAULT_CATEGORIES):
        session.add(
            LmsCategory(organisation_id=org_id, slug=slug, name=name, is_system=True, sort_order=idx)
        )
    session.flush()


def update_settings(session: Session, ctx: OrganisationContext, payload: dict[str, Any]) -> dict[str, Any]:
    row = _settings(session, ctx.organisation_id)
    for key in (
        "enabled",
        "privacy_review_complete",
        "default_certificate_validity_days",
        "tenant_courses_enabled",
        "reminder_config",
    ):
        if key in payload and payload[key] is not None:
            setattr(row, key, payload[key])
    if row.enabled:
        ensure_categories(session, ctx.organisation_id)
    session.flush()
    record_event(
        session,
        action=audit_events.LMS_SETTINGS_UPDATE,
        resource_type="lms_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="LMS settings updated",
    )
    return settings_dict(row)


def create_course(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> LmsCourse:
    access.require_manage(ctx)
    assert_addon(session, get_settings(), ctx.organisation_id)
    course = LmsCourse(
        organisation_id=ctx.organisation_id,
        category_id=data["category_id"],
        title=data["title"],
        description=data.get("description"),
        instructor=data.get("instructor"),
        learning_objectives=data.get("learning_objectives") or [],
        duration_minutes=data.get("duration_minutes"),
        difficulty=data.get("difficulty"),
        certificate_eligible=data.get("certificate_eligible", True),
        pass_mark_percent=int(data.get("pass_mark_percent", 80)),
        certificate_validity_days=data.get("certificate_validity_days"),
        staff_only=data.get("staff_only", True),
        tenant_visible=data.get("tenant_visible", False),
        status="draft",
    )
    session.add(course)
    session.flush()
    record_event(
        session,
        action=audit_events.LMS_COURSE_CREATED,
        resource_type="lms_course",
        resource_id=str(course.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="LMS course created",
    )
    return course


def publish_course(session: Session, ctx: OrganisationContext, course_id: UUID) -> LmsCourse:
    access.require_manage(ctx)
    course = session.get(LmsCourse, course_id)
    if course is None or course.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Course not found")
    course.status = "published"
    session.flush()
    return course


def course_to_dict(course: LmsCourse) -> dict[str, Any]:
    return {
        "id": str(course.id),
        "title": course.title,
        "description": course.description,
        "category_id": str(course.category_id),
        "status": course.status,
        "duration_minutes": course.duration_minutes,
        "difficulty": course.difficulty,
        "certificate_eligible": course.certificate_eligible,
        "staff_only": course.staff_only,
        "tenant_visible": course.tenant_visible,
    }


def assign_course(
    session: Session,
    ctx: OrganisationContext,
    *,
    course_id: UUID,
    target_type: str,
    target_value: str,
    mandatory: bool,
    due_date: date | None,
) -> LmsCourseAssignment:
    from app.rbac.permissions import Permission
    from app.rbac.service import require_permission

    require_permission(ctx.authorization, Permission.LMS_ASSIGN)
    assignment = LmsCourseAssignment(
        organisation_id=ctx.organisation_id,
        course_id=course_id,
        target_type=target_type,
        target_value=target_value,
        mandatory=mandatory,
        due_date=due_date,
        created_by_user_id=ctx.user_id,
    )
    session.add(assignment)
    session.flush()
    sync_assignments(session, ctx.organisation_id, assignment)
    _notify(session, ctx.organisation_id, target_type, target_value, "New training course assigned")
    return assignment


def sync_assignments(session: Session, org_id: UUID, assignment: LmsCourseAssignment | None = None) -> int:
    q = select(LmsCourseAssignment).where(LmsCourseAssignment.organisation_id == org_id)
    if assignment:
        q = q.where(LmsCourseAssignment.id == assignment.id)
    assignments = session.scalars(q).all()
    created = 0
    for row in assignments:
        user_ids = _resolve_assignment_users(session, org_id, row)
        for uid in user_ids:
            exists = session.scalar(
                select(LmsEnrollment).where(
                    LmsEnrollment.organisation_id == org_id,
                    LmsEnrollment.course_id == row.course_id,
                    LmsEnrollment.user_id == uid,
                )
            )
            if exists:
                continue
            session.add(
                LmsEnrollment(
                    organisation_id=org_id,
                    course_id=row.course_id,
                    user_id=uid,
                    due_date=row.due_date,
                    status="assigned",
                )
            )
            created += 1
    session.flush()
    return created


def _resolve_assignment_users(session: Session, org_id: UUID, row: LmsCourseAssignment) -> list[UUID]:
    from app.db.models.enums import MembershipStatus
    from app.db.models.membership import OrganisationMembership

    if row.target_type == "user":
        return [UUID(row.target_value)]
    if row.target_type == "organisation":
        return list(
            session.scalars(
                select(OrganisationMembership.user_id).where(
                    OrganisationMembership.organisation_id == org_id,
                    OrganisationMembership.status == MembershipStatus.ACTIVE,
                )
            ).all()
        )
    if row.target_type == "role":
        return list(
            session.scalars(
                select(OrganisationMembership.user_id).where(
                    OrganisationMembership.organisation_id == org_id,
                    OrganisationMembership.role == row.target_value,
                    OrganisationMembership.status == MembershipStatus.ACTIVE,
                )
            ).all()
        )
    if row.target_type == "category":
        courses = session.scalars(
            select(LmsCourse.id).join(LmsCategory).where(
                LmsCategory.organisation_id == org_id,
                LmsCategory.slug == row.target_value,
            )
        ).all()
        return []
    return []


def learner_dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    access.require_learn(ctx)
    assert_addon(session, get_settings(), ctx.organisation_id)
    settings = _settings(session, ctx.organisation_id)
    enrollments = session.scalars(
        select(LmsEnrollment).where(
            LmsEnrollment.organisation_id == ctx.organisation_id,
            LmsEnrollment.user_id == ctx.user_id,
        )
    ).all()
    certs = session.scalars(
        select(LmsCertificate).join(LmsEnrollment).where(
            LmsCertificate.organisation_id == ctx.organisation_id,
            LmsEnrollment.user_id == ctx.user_id,
        )
    ).all()
    by_status = {"assigned": 0, "in_progress": 0, "completed": 0}
    for e in enrollments:
        recompute_progress(session, e)
        by_status[e.status] = by_status.get(e.status, 0) + 1
    soon = _now() + timedelta(days=30)
    expiring = sum(1 for c in certs if c.expires_at and c.expires_at < soon and c.status == "valid")
    return {
        "enrollments_by_status": by_status,
        "certificates_count": len(certs),
        "expiring_certificates": expiring,
        "total_enrollments": len(enrollments),
    }


def list_learner_courses(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    access.require_learn(ctx)
    settings = _settings(session, ctx.organisation_id)
    rows = session.execute(
        select(LmsEnrollment, LmsCourse)
        .join(LmsCourse, LmsCourse.id == LmsEnrollment.course_id)
        .where(LmsEnrollment.organisation_id == ctx.organisation_id, LmsEnrollment.user_id == ctx.user_id)
    ).all()
    out: list[dict[str, Any]] = []
    for enrollment, course in rows:
        try:
            access.assert_course_visible(ctx, course, settings.tenant_courses_enabled)
        except HTTPException:
            continue
        recompute_progress(session, enrollment)
        out.append({**course_to_dict(course), "enrollment_id": str(enrollment.id), "progress_percent": enrollment.progress_percent, "status": enrollment.status})
    return out


def complete_lesson(session: Session, ctx: OrganisationContext, enrollment_id: UUID, lesson_id: UUID) -> None:
    enrollment = session.get(LmsEnrollment, enrollment_id)
    if enrollment is None or enrollment.user_id != ctx.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Enrollment not found")
    exists = session.scalar(
        select(LmsLessonCompletion).where(
            LmsLessonCompletion.enrollment_id == enrollment_id,
            LmsLessonCompletion.lesson_id == lesson_id,
        )
    )
    if exists is None:
        session.add(
            LmsLessonCompletion(
                organisation_id=ctx.organisation_id,
                enrollment_id=enrollment_id,
                lesson_id=lesson_id,
            )
        )
    enrollment.status = "in_progress"
    session.flush()
    recompute_progress(session, enrollment)
    maybe_complete_course(session, ctx, enrollment)


def recompute_progress(session: Session, enrollment: LmsEnrollment) -> None:
    lesson_ids = session.scalars(
        select(LmsLesson.id)
        .join(LmsCourseModule, LmsCourseModule.id == LmsLesson.module_id)
        .where(LmsCourseModule.course_id == enrollment.course_id)
    ).all()
    if not lesson_ids:
        enrollment.progress_percent = 0
        return
    done = session.scalar(
        select(func.count()).select_from(LmsLessonCompletion).where(
            LmsLessonCompletion.enrollment_id == enrollment.id,
            LmsLessonCompletion.lesson_id.in_(lesson_ids),
        )
    ) or 0
    enrollment.progress_percent = int(round(100 * done / len(lesson_ids)))
    session.flush()


def maybe_complete_course(session: Session, ctx: OrganisationContext, enrollment: LmsEnrollment) -> None:
    course = session.get(LmsCourse, enrollment.course_id)
    if course is None or enrollment.progress_percent < 100:
        return
    final = session.scalar(
        select(LmsQuiz).where(LmsQuiz.course_id == course.id, LmsQuiz.is_final_assessment.is_(True))
    )
    if final:
        passed = session.scalar(
            select(LmsAssessmentAttempt).where(
                LmsAssessmentAttempt.enrollment_id == enrollment.id,
                LmsAssessmentAttempt.quiz_id == final.id,
                LmsAssessmentAttempt.passed.is_(True),
            )
        )
        if not passed:
            return
    enrollment.status = "completed"
    enrollment.completed_at = _now()
    session.flush()
    if course.certificate_eligible:
        user = session.get(User, enrollment.user_id)
        if user:
            settings = _settings(session, ctx.organisation_id)
            validity = course.certificate_validity_days or settings.default_certificate_validity_days
            cert = certificates.issue_certificate(
                session,
                org_id=ctx.organisation_id,
                enrollment=enrollment,
                course=course,
                learner=user,
                provider_name=course.instructor,
                validity_days=validity,
            )
            _notify_user(session, ctx.organisation_id, enrollment.user_id, "Certificate issued", cert.certificate_number)


def submit_assessment(
    session: Session,
    ctx: OrganisationContext,
    *,
    quiz_id: UUID,
    enrollment_id: UUID,
    answers: list[dict[str, Any]],
) -> LmsAssessmentAttempt:
    access.require_learn(ctx)
    quiz = session.get(LmsQuiz, quiz_id)
    enrollment = session.get(LmsEnrollment, enrollment_id)
    if quiz is None or enrollment is None or enrollment.user_id != ctx.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    if quiz.attempt_limit:
        count = session.scalar(
            select(func.count()).select_from(LmsAssessmentAttempt).where(
                LmsAssessmentAttempt.quiz_id == quiz_id,
                LmsAssessmentAttempt.enrollment_id == enrollment_id,
            )
        ) or 0
        if count >= quiz.attempt_limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Attempt limit reached")
    attempt = LmsAssessmentAttempt(
        organisation_id=ctx.organisation_id,
        quiz_id=quiz_id,
        enrollment_id=enrollment_id,
        user_id=ctx.user_id,
    )
    session.add(attempt)
    session.flush()
    questions = {q.id: q for q in session.scalars(select(LmsQuestion).where(LmsQuestion.quiz_id == quiz_id)).all()}
    scoring: list[tuple[bool | None, bool]] = []
    pending_manual = False
    for item in answers:
        qid = UUID(str(item["question_id"]))
        question = questions.get(qid)
        if question is None:
            continue
        correct, auto = assessments.score_answer(question, item.get("answer"))
        scoring.append((correct, auto))
        if not auto:
            pending_manual = True
        session.add(
            LmsAssessmentAnswer(
                organisation_id=ctx.organisation_id,
                attempt_id=attempt.id,
                question_id=qid,
                answer=item.get("answer"),
                auto_scored=auto,
                correct=correct,
            )
        )
    if pending_manual:
        attempt.status = "pending_manual"
        attempt.passed = None
    else:
        score = assessments.compute_score_percent(scoring)
        attempt.score_percent = score
        attempt.passed = score is not None and score >= quiz.pass_mark_percent
        attempt.status = "marked"
        maybe_complete_course(session, ctx, enrollment)
    session.flush()
    record_event(
        session,
        action=audit_events.LMS_ASSESSMENT_SUBMITTED,
        resource_type="lms_assessment_attempt",
        resource_id=str(attempt.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="LMS assessment submitted",
        metadata={"pending_manual": pending_manual},
    )
    return attempt


def manual_mark_attempt(
    session: Session,
    ctx: OrganisationContext,
    attempt_id: UUID,
    *,
    passed: bool,
    feedback: str | None,
) -> LmsAssessmentAttempt:
    access.require_manage(ctx)
    attempt = session.get(LmsAssessmentAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    attempt.passed = passed
    attempt.feedback = feedback
    attempt.status = "marked"
    session.flush()
    if passed:
        enrollment = session.get(LmsEnrollment, attempt.enrollment_id)
        if enrollment:
            maybe_complete_course(session, ctx, enrollment)
    return attempt


def admin_dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    from app.rbac.permissions import Permission
    from app.rbac.service import require_permission

    require_permission(ctx.authorization, Permission.LMS_REPORTS)
    org = ctx.organisation_id
    courses = session.scalar(select(func.count()).select_from(LmsCourse).where(LmsCourse.organisation_id == org)) or 0
    published = (
        session.scalar(
            select(func.count()).select_from(LmsCourse).where(
                LmsCourse.organisation_id == org, LmsCourse.status == "published"
            )
        )
        or 0
    )
    enrollments = session.scalar(select(func.count()).select_from(LmsEnrollment).where(LmsEnrollment.organisation_id == org)) or 0
    completed = (
        session.scalar(
            select(func.count()).select_from(LmsEnrollment).where(
                LmsEnrollment.organisation_id == org, LmsEnrollment.status == "completed"
            )
        )
        or 0
    )
    certs = session.scalar(select(func.count()).select_from(LmsCertificate).where(LmsCertificate.organisation_id == org)) or 0
    pending = (
        session.scalar(
            select(func.count()).select_from(LmsAssessmentAttempt).where(
                LmsAssessmentAttempt.organisation_id == org,
                LmsAssessmentAttempt.status == "pending_manual",
            )
        )
        or 0
    )
    return {
        "total_courses": int(courses),
        "published_courses": int(published),
        "enrollments": int(enrollments),
        "completed_enrollments": int(completed),
        "certificates_issued": int(certs),
        "pending_assessments": int(pending),
    }


def verify_certificate(session: Session, org_id: UUID, verification_reference: str) -> dict[str, Any]:
    cert = session.scalar(
        select(LmsCertificate).where(
            LmsCertificate.organisation_id == org_id,
            LmsCertificate.verification_reference == verification_reference,
        )
    )
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    if cert.expires_at and cert.expires_at < _now() and cert.status == "valid":
        cert.status = "expired"
        session.flush()
    return {
        "certificate_number": cert.certificate_number,
        "learner_name": cert.learner_name,
        "course_title": cert.course_title,
        "status": cert.status,
        "issued_at": cert.issued_at.isoformat(),
        "expires_at": cert.expires_at.isoformat() if cert.expires_at else None,
    }


def _notify(session: Session, org_id: UUID, target_type: str, target_value: str, subject: str) -> None:
    return


def _notify_user(session: Session, org_id: UUID, user_id: UUID, subject: str, ref: str) -> None:
    provider = get_notification_provider()
    provider.send(
        session,
        ReminderMessage(
            organisation_id=str(org_id),
            recipient_user_id=str(user_id),
            subject=subject,
            body="Open HMore learning to view details.",
            channel="in_app",
            target_type="lms",
            target_id=ref,
            idempotency_key=f"lms:{user_id}:{subject}:{ref}",
            essential_operational=True,
        ),
    )


def refresh_certificate_statuses(session: Session, org_id: UUID) -> int:
    certs = session.scalars(
        select(LmsCertificate).where(
            LmsCertificate.organisation_id == org_id,
            LmsCertificate.status == "valid",
            LmsCertificate.expires_at.is_not(None),
        )
    ).all()
    count = 0
    now = _now()
    for cert in certs:
        if cert.expires_at and cert.expires_at < now:
            cert.status = "expired"
            count += 1
    session.flush()
    return count
