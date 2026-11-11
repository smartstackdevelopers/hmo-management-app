"""F5.3 skills assessment, CV builder, applications and career roadmap."""

from __future__ import annotations

import copy
import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.employment import (
    TenantCareerGoal,
    TenantCv,
    TenantInterviewNote,
    TenantJobApplication,
    TenantJobApplicationEvent,
    TenantSkillAssessment,
)
from app.db.models.enums import HMoreRole
from app.db.models.tenant import Tenant
from app.employment.access import resolve_own_tenant, resolve_tenant_for_staff_or_self
from app.employment.constants import (
    APPLICATION_STATUSES,
    COMMON_INTERVIEW_QUESTIONS,
    CV_TEMPLATES,
    DEFAULT_CV_SECTIONS,
    INTERVIEW_CHECKLIST_DEFAULT,
    SKILL_CATEGORIES,
    SKILL_LEVELS,
)
from app.employment.pdf import build_cv_pdf
from app.employment.schemas import (
    ApplicationCreate,
    ApplicationDashboard,
    ApplicationOut,
    ApplicationUpdate,
    AssessmentOut,
    AssessmentUpdate,
    CareerGoalOut,
    CareerGoalWrite,
    CvAssistRequest,
    CvAssistResponse,
    CvCreate,
    CvOut,
    CvUpdate,
    InterviewNoteOut,
    InterviewNoteWrite,
    RoadmapOut,
    StaffEmploymentSummary,
)
from app.storage import service as storage_service
from app.tenancy.context import OrganisationContext


def _audit(session: Session, ctx: OrganisationContext, *, action: str, resource_type: str, resource_id, summary: str, metadata: dict | None = None) -> None:
    record_event(
        session,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary=summary,
        metadata=metadata or {},
    )


def _completion_percent(row: TenantSkillAssessment) -> int:
    checks = [
        bool(row.skills_json),
        bool(row.experiences_json) or bool(row.education_json) or bool(row.qualifications_json),
        bool(row.career_interests_json) or bool(row.preferred_work_types_json),
        bool((row.employment_goals or "").strip()),
        bool(row.languages_json) or bool(row.certificates_json),
    ]
    return int(round(100 * sum(1 for item in checks if item) / len(checks)))


def _assessment_summary(row: TenantSkillAssessment) -> dict[str, Any]:
    skills = row.skills_json or []
    by_category: dict[str, int] = {}
    for skill in skills:
        if isinstance(skill, dict):
            cat = str(skill.get("category") or "other")
            by_category[cat] = by_category.get(cat, 0) + 1
    return {
        "skill_count": len(skills),
        "skills_by_category": by_category,
        "experience_count": len(row.experiences_json or []),
        "education_count": len(row.education_json or []),
        "has_goals": bool((row.employment_goals or "").strip()),
        "note": "Skill levels are self-reported and are not formally verified qualifications.",
    }


def _assessment_out(row: TenantSkillAssessment) -> AssessmentOut:
    return AssessmentOut(
        id=row.id,
        tenant_id=row.tenant_id,
        status=row.status,
        skills=row.skills_json or [],
        experiences=row.experiences_json or [],
        education=row.education_json or [],
        qualifications=row.qualifications_json or [],
        certificates=row.certificates_json or [],
        languages=row.languages_json or [],
        career_interests=row.career_interests_json or [],
        preferred_work_types=row.preferred_work_types_json or [],
        employment_goals=row.employment_goals,
        completion_percent=row.completion_percent,
        summary=_assessment_summary(row),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_skill_categories() -> dict[str, list[str]]:
    return {"categories": list(SKILL_CATEGORIES), "levels": list(SKILL_LEVELS)}


def get_or_create_assessment(session: Session, ctx: OrganisationContext) -> AssessmentOut:
    tenant = resolve_own_tenant(session, ctx)
    row = session.scalar(
        select(TenantSkillAssessment).where(
            TenantSkillAssessment.organisation_id == ctx.organisation_id,
            TenantSkillAssessment.tenant_id == tenant.id,
        )
    )
    if row is None:
        row = TenantSkillAssessment(
            organisation_id=ctx.organisation_id,
            tenant_id=tenant.id,
            skills_json=[],
            experiences_json=[],
            education_json=[],
            qualifications_json=[],
            certificates_json=[],
            languages_json=[],
            career_interests_json=[],
            preferred_work_types_json=[],
            status="in_progress",
            completion_percent=0,
        )
        session.add(row)
        session.flush()
        _audit(
            session,
            ctx,
            action=audit_events.EMPLOYMENT_ASSESSMENT_UPSERT,
            resource_type="tenant_skill_assessment",
            resource_id=row.id,
            summary="Skills assessment created",
        )
    return _assessment_out(row)


def update_assessment(session: Session, ctx: OrganisationContext, data: AssessmentUpdate) -> AssessmentOut:
    tenant = resolve_own_tenant(session, ctx)
    row = session.scalar(
        select(TenantSkillAssessment).where(
            TenantSkillAssessment.organisation_id == ctx.organisation_id,
            TenantSkillAssessment.tenant_id == tenant.id,
        )
    )
    if row is None:
        get_or_create_assessment(session, ctx)
        row = session.scalar(
            select(TenantSkillAssessment).where(
                TenantSkillAssessment.organisation_id == ctx.organisation_id,
                TenantSkillAssessment.tenant_id == tenant.id,
            )
        )
    assert row is not None
    payload = data.model_dump(exclude_unset=True)
    if "skills" in payload and payload["skills"] is not None:
        normalised_skills = []
        for skill in payload["skills"]:
            item = skill if isinstance(skill, dict) else skill
            if not isinstance(item, dict):
                raise HTTPException(status_code=422, detail="Invalid skill payload")
            category = item.get("category") or "other"
            if category not in SKILL_CATEGORIES:
                raise HTTPException(status_code=422, detail="Invalid skill category")
            if item.get("level") and item["level"] not in SKILL_LEVELS:
                raise HTTPException(status_code=422, detail="Invalid skill level")
            normalised_skills.append(item)
        row.skills_json = normalised_skills
    mapping = {
        "experiences": "experiences_json",
        "education": "education_json",
        "qualifications": "qualifications_json",
        "certificates": "certificates_json",
        "languages": "languages_json",
        "career_interests": "career_interests_json",
        "preferred_work_types": "preferred_work_types_json",
        "employment_goals": "employment_goals",
    }
    for src, dest in mapping.items():
        if src in payload:
            setattr(row, dest, payload[src])
    if payload.get("mark_completed"):
        row.status = "completed"
    else:
        row.status = "in_progress"
    row.completion_percent = _completion_percent(row)
    if row.completion_percent >= 80 and payload.get("mark_completed") is not False:
        # Do not force completed; only when requested above.
        pass
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.EMPLOYMENT_ASSESSMENT_UPSERT,
        resource_type="tenant_skill_assessment",
        resource_id=row.id,
        summary="Skills assessment updated",
    )
    return _assessment_out(row)


def _cv_completion(content: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "personal_profile": bool((content.get("personal_profile") or "").strip()),
        "contact": bool(content.get("contact")),
        "employment": bool(content.get("employment")),
        "education": bool(content.get("education")),
        "skills": bool(content.get("skills")),
    }
    present = sum(1 for value in checks.values() if value)
    suggestions: list[str] = []
    if not checks["personal_profile"]:
        suggestions.append("Add a short personal profile.")
    if not checks["contact"]:
        suggestions.append("Add contact information.")
    if not checks["skills"]:
        suggestions.append("Add skills from your assessment or write them manually.")
    if not checks["employment"] and not checks["education"]:
        suggestions.append("Add education, volunteering or projects if you have limited work history.")
    return {
        "percent": int(round(100 * present / len(checks))),
        "checks": checks,
        "suggestions": suggestions,
        "disclaimer": "A complete CV does not guarantee employment.",
    }


def _cv_out(row: TenantCv) -> CvOut:
    content = row.content_json or {}
    return CvOut(
        id=row.id,
        tenant_id=row.tenant_id,
        title=row.title,
        template_id=row.template_id,
        content=content,
        section_order=row.section_order_json or list(DEFAULT_CV_SECTIONS),
        version=row.version,
        is_default=row.is_default,
        pdf_file_id=row.pdf_file_id,
        completion=_cv_completion(content),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _seed_content_from_assessment(assessment: TenantSkillAssessment | None, tenant: Tenant) -> dict[str, Any]:
    content: dict[str, Any] = {
        "personal_profile": "",
        "contact": {
            "name": tenant.preferred_name or tenant.full_name or "",
            "email": tenant.email or "",
            "phone": tenant.phone or "",
        },
        "employment": [],
        "education": [],
        "qualifications": [],
        "skills": [],
        "certificates": [],
        "volunteer": [],
        "projects": [],
        "languages": [],
        "references": [],
    }
    if assessment is None:
        return content
    for exp in assessment.experiences_json or []:
        if not isinstance(exp, dict):
            continue
        kind = exp.get("kind")
        target = "employment" if kind == "employment" else "volunteer" if kind == "volunteer" else "projects"
        content[target].append(exp)
    content["education"] = list(assessment.education_json or [])
    content["qualifications"] = list(assessment.qualifications_json or [])
    content["certificates"] = list(assessment.certificates_json or [])
    content["languages"] = list(assessment.languages_json or [])
    content["skills"] = [
        {
            "name": s.get("name"),
            "category": s.get("category"),
            "level": s.get("level"),
            "self_reported": True,
        }
        for s in (assessment.skills_json or [])
        if isinstance(s, dict)
    ]
    return content


def list_cvs(session: Session, ctx: OrganisationContext) -> dict[str, list[CvOut]]:
    tenant = resolve_own_tenant(session, ctx)
    rows = list(
        session.scalars(
            select(TenantCv)
            .where(TenantCv.organisation_id == ctx.organisation_id, TenantCv.tenant_id == tenant.id)
            .order_by(TenantCv.updated_at.desc())
        )
    )
    return {"items": [_cv_out(row) for row in rows]}


def create_cv(session: Session, ctx: OrganisationContext, data: CvCreate) -> CvOut:
    tenant = resolve_own_tenant(session, ctx)
    if data.template_id not in CV_TEMPLATES:
        raise HTTPException(status_code=422, detail="Invalid template_id")
    assessment = session.scalar(
        select(TenantSkillAssessment).where(
            TenantSkillAssessment.organisation_id == ctx.organisation_id,
            TenantSkillAssessment.tenant_id == tenant.id,
        )
    )
    content = data.content.model_dump(exclude_none=True) if data.content else {}
    if data.seed_from_assessment:
        seeded = _seed_content_from_assessment(assessment, tenant)
        seeded.update(content)
        content = seeded
    section_order = data.section_order or list(DEFAULT_CV_SECTIONS)
    if data.is_default:
        _clear_default_cvs(session, ctx.organisation_id, tenant.id)
    row = TenantCv(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        title=data.title.strip(),
        template_id=data.template_id,
        content_json=content,
        section_order_json=section_order,
        version=1,
        is_default=data.is_default,
    )
    session.add(row)
    session.flush()
    _audit(session, ctx, action=audit_events.EMPLOYMENT_CV_CREATE, resource_type="tenant_cv", resource_id=row.id, summary="CV created")
    return _cv_out(row)


def _clear_default_cvs(session: Session, organisation_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    rows = session.scalars(
        select(TenantCv).where(
            TenantCv.organisation_id == organisation_id,
            TenantCv.tenant_id == tenant_id,
            TenantCv.is_default.is_(True),
        )
    )
    for row in rows:
        row.is_default = False
        session.add(row)


def get_cv(session: Session, ctx: OrganisationContext, cv_id: uuid.UUID) -> CvOut:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(TenantCv, cv_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="CV not found")
    return _cv_out(row)


def update_cv(session: Session, ctx: OrganisationContext, cv_id: uuid.UUID, data: CvUpdate) -> CvOut:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(TenantCv, cv_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="CV not found")
    payload = data.model_dump(exclude_unset=True)
    if "template_id" in payload and payload["template_id"] not in CV_TEMPLATES:
        raise HTTPException(status_code=422, detail="Invalid template_id")
    if "title" in payload and payload["title"]:
        row.title = payload["title"].strip()
    if "template_id" in payload and payload["template_id"]:
        row.template_id = payload["template_id"]
    if "content" in payload and payload["content"] is not None:
        # Merge section updates so partial edits do not wipe other CV sections.
        merged = dict(row.content_json or {})
        incoming = payload["content"]
        if isinstance(incoming, dict):
            for key, value in incoming.items():
                if value is not None:
                    merged[key] = value
        row.content_json = merged
    if "section_order" in payload and payload["section_order"] is not None:
        row.section_order_json = payload["section_order"]
    if payload.get("is_default") is True:
        _clear_default_cvs(session, ctx.organisation_id, tenant.id)
        row.is_default = True
    elif payload.get("is_default") is False:
        row.is_default = False
    row.version = int(row.version or 1) + 1
    row.pdf_file_id = None  # stale PDF must be regenerated
    session.add(row)
    session.flush()
    _audit(session, ctx, action=audit_events.EMPLOYMENT_CV_UPDATE, resource_type="tenant_cv", resource_id=row.id, summary="CV updated")
    return _cv_out(row)


def duplicate_cv(session: Session, ctx: OrganisationContext, cv_id: uuid.UUID) -> CvOut:
    tenant = resolve_own_tenant(session, ctx)
    source = session.get(TenantCv, cv_id)
    if source is None or source.organisation_id != ctx.organisation_id or source.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="CV not found")
    row = TenantCv(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        title=f"{source.title} (copy)",
        template_id=source.template_id,
        content_json=copy.deepcopy(source.content_json or {}),
        section_order_json=list(source.section_order_json or DEFAULT_CV_SECTIONS),
        version=1,
        is_default=False,
    )
    session.add(row)
    session.flush()
    _audit(session, ctx, action=audit_events.EMPLOYMENT_CV_CREATE, resource_type="tenant_cv", resource_id=row.id, summary="CV duplicated")
    return _cv_out(row)


def delete_cv(session: Session, ctx: OrganisationContext, cv_id: uuid.UUID) -> dict[str, str]:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(TenantCv, cv_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="CV not found")
    session.delete(row)
    session.flush()
    _audit(session, ctx, action=audit_events.EMPLOYMENT_CV_DELETE, resource_type="tenant_cv", resource_id=cv_id, summary="CV deleted")
    return {"status": "deleted"}


def generate_cv_pdf(
    session: Session,
    ctx: OrganisationContext,
    cv_id: uuid.UUID,
    *,
    settings=None,
    backend=None,
) -> CvOut:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(TenantCv, cv_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="CV not found")
    pdf_bytes = build_cv_pdf(
        title=row.title,
        template_id=row.template_id,
        content=row.content_json or {},
        section_order=row.section_order_json or list(DEFAULT_CV_SECTIONS),
    )
    upload_kwargs: dict[str, Any] = {
        "filename": f"{row.title[:40].replace(' ', '_')}.pdf",
        "declared_content_type": "application/pdf",
        "data": pdf_bytes,
        "resource_type": "tenant_cv",
        "resource_id": str(row.id),
    }
    if settings is not None:
        upload_kwargs["settings"] = settings
    if backend is not None:
        upload_kwargs["backend"] = backend
    uploaded = storage_service.upload_file(session, ctx, **upload_kwargs)
    row.pdf_file_id = uuid.UUID(uploaded["id"])
    session.add(row)
    session.flush()
    _audit(session, ctx, action=audit_events.EMPLOYMENT_CV_PDF, resource_type="tenant_cv", resource_id=row.id, summary="CV PDF generated")
    return _cv_out(row)


def download_cv_pdf(
    session: Session,
    ctx: OrganisationContext,
    cv_id: uuid.UUID,
    *,
    settings=None,
    backend=None,
) -> Response:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(TenantCv, cv_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="CV not found")
    if row.pdf_file_id is None:
        generate_cv_pdf(session, ctx, cv_id, settings=settings, backend=backend)
        session.refresh(row)
    assert row.pdf_file_id is not None
    download_kwargs: dict[str, Any] = {}
    if backend is not None:
        download_kwargs["backend"] = backend
    file_row, data = storage_service.download_file(session, ctx, row.pdf_file_id, **download_kwargs)
    return Response(
        content=data,
        media_type=file_row.content_type or "application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{file_row.original_filename}"',
            "Cache-Control": "private, no-store",
        },
    )


def assist_cv_wording(session: Session, ctx: OrganisationContext, body: CvAssistRequest) -> CvAssistResponse:
    """Optional AI assist. Never invents facts; returns suggestion for human approval."""
    resolve_own_tenant(session, ctx)
    original = body.original_text.strip()
    try:
        from app.employment.ai_client import rewrite_cv_text

        suggested = rewrite_cv_text(session, ctx, original_text=original, field=body.field)
        provider = "ai_service"
    except HTTPException as exc:
        if exc.status_code in {402, 503}:
            # Graceful local tidy-up that does not invent content.
            suggested = " ".join(original.split())
            if suggested and suggested[0].islower():
                suggested = suggested[0].upper() + suggested[1:]
            provider = "local_cleanup"
        else:
            raise
    return CvAssistResponse(
        field=body.field,
        original_text=original,
        suggested_text=suggested,
        provider=provider,
        requires_approval=True,
        disclaimer="Review carefully. AI must not invent jobs, dates, qualifications or achievements.",
    )


def _application_out(row: TenantJobApplication) -> ApplicationOut:
    return ApplicationOut.model_validate(row)


def list_applications(
    session: Session,
    ctx: OrganisationContext,
    *,
    status_filter: str | None,
    q: str | None,
    archived: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    tenant = resolve_own_tenant(session, ctx)
    if status_filter and status_filter not in APPLICATION_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")
    filters = [
        TenantJobApplication.organisation_id == ctx.organisation_id,
        TenantJobApplication.tenant_id == tenant.id,
        TenantJobApplication.is_archived.is_(archived),
    ]
    if status_filter:
        filters.append(TenantJobApplication.status == status_filter)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                TenantJobApplication.employer_name.ilike(pattern),
                TenantJobApplication.job_title.ilike(pattern),
                TenantJobApplication.job_location.ilike(pattern),
            )
        )
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = session.scalar(select(func.count()).select_from(TenantJobApplication).where(*filters)) or 0
    rows = list(
        session.scalars(
            select(TenantJobApplication)
            .where(*filters)
            .order_by(TenantJobApplication.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return {"items": [_application_out(row) for row in rows], "page": page, "page_size": page_size, "total": total}


def create_application(session: Session, ctx: OrganisationContext, data: ApplicationCreate) -> ApplicationOut:
    tenant = resolve_own_tenant(session, ctx)
    if data.status not in APPLICATION_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")
    if data.linked_cv_id:
        cv = session.get(TenantCv, data.linked_cv_id)
        if cv is None or cv.tenant_id != tenant.id or cv.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=404, detail="Linked CV not found")
    row = TenantJobApplication(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        employer_name=data.employer_name.strip(),
        job_title=data.job_title.strip(),
        job_location=data.job_location,
        application_date=data.application_date,
        source=data.source,
        linked_cv_id=data.linked_cv_id,
        contact_info=data.contact_info,
        status=data.status,
        interview_at=data.interview_at,
        follow_up_at=data.follow_up_at,
        notes=data.notes,
    )
    session.add(row)
    session.flush()
    session.add(
        TenantJobApplicationEvent(
            organisation_id=ctx.organisation_id,
            application_id=row.id,
            from_status=None,
            to_status=row.status,
            notes="Application created",
            actor_user_id=ctx.user_id,
        )
    )
    session.flush()
    _audit(session, ctx, action=audit_events.EMPLOYMENT_APPLICATION_UPSERT, resource_type="tenant_job_application", resource_id=row.id, summary="Job application created")
    return _application_out(row)


def update_application(
    session: Session, ctx: OrganisationContext, application_id: uuid.UUID, data: ApplicationUpdate
) -> ApplicationOut:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(TenantJobApplication, application_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Application not found")
    payload = data.model_dump(exclude_unset=True)
    if "status" in payload and payload["status"] is not None:
        if payload["status"] not in APPLICATION_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid status")
        if payload["status"] != row.status:
            session.add(
                TenantJobApplicationEvent(
                    organisation_id=ctx.organisation_id,
                    application_id=row.id,
                    from_status=row.status,
                    to_status=payload["status"],
                    notes="Status updated by tenant",
                    actor_user_id=ctx.user_id,
                )
            )
    for key, value in payload.items():
        setattr(row, key, value)
    session.add(row)
    session.flush()
    _audit(session, ctx, action=audit_events.EMPLOYMENT_APPLICATION_UPSERT, resource_type="tenant_job_application", resource_id=row.id, summary="Job application updated")
    return _application_out(row)


def delete_application(session: Session, ctx: OrganisationContext, application_id: uuid.UUID) -> dict[str, str]:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(TenantJobApplication, application_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Application not found")
    session.delete(row)
    session.flush()
    return {"status": "deleted"}


def application_dashboard(session: Session, ctx: OrganisationContext) -> ApplicationDashboard:
    tenant = resolve_own_tenant(session, ctx)
    rows = list(
        session.scalars(
            select(TenantJobApplication).where(
                TenantJobApplication.organisation_id == ctx.organisation_id,
                TenantJobApplication.tenant_id == tenant.id,
                TenantJobApplication.is_archived.is_(False),
            )
        )
    )
    now = datetime.now(timezone.utc)
    upcoming = [
        row
        for row in rows
        if row.interview_at is not None and row.interview_at >= now and row.status in {"interview_scheduled", "acknowledged", "applied"}
    ]
    upcoming.sort(key=lambda item: item.interview_at or now)
    follow_ups = [
        row
        for row in rows
        if row.follow_up_at is not None and row.follow_up_at.date() <= date.today() and row.status not in {"rejected", "withdrawn", "offer_received"}
    ]
    return ApplicationDashboard(
        total=len(rows),
        preparing=sum(1 for row in rows if row.status in {"interested", "preparing"}),
        submitted=sum(1 for row in rows if row.status in {"applied", "acknowledged"}),
        interviews_scheduled=sum(1 for row in rows if row.status == "interview_scheduled"),
        offers=sum(1 for row in rows if row.status == "offer_received"),
        rejected=sum(1 for row in rows if row.status == "rejected"),
        upcoming_interviews=[_application_out(row) for row in upcoming[:10]],
        follow_ups_due=[_application_out(row) for row in follow_ups[:10]],
    )


def list_career_goals(session: Session, ctx: OrganisationContext) -> dict[str, list[CareerGoalOut]]:
    tenant = resolve_own_tenant(session, ctx)
    rows = list(
        session.scalars(
            select(TenantCareerGoal)
            .where(TenantCareerGoal.organisation_id == ctx.organisation_id, TenantCareerGoal.tenant_id == tenant.id)
            .order_by(TenantCareerGoal.created_at.desc())
        )
    )
    return {
        "items": [
            CareerGoalOut(
                id=row.id,
                tenant_id=row.tenant_id,
                title=row.title,
                description=row.description,
                suggested_activities=row.suggested_activities_json or [],
                status=row.status,
                progress_notes=row.progress_notes,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    }


def create_career_goal(session: Session, ctx: OrganisationContext, data: CareerGoalWrite) -> CareerGoalOut:
    tenant = resolve_own_tenant(session, ctx)
    if data.status not in {"pending", "in_progress", "completed"}:
        raise HTTPException(status_code=422, detail="Invalid status")
    row = TenantCareerGoal(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        title=data.title.strip(),
        description=data.description,
        suggested_activities_json=data.suggested_activities or [],
        status=data.status,
        progress_notes=data.progress_notes,
    )
    session.add(row)
    session.flush()
    return CareerGoalOut(
        id=row.id,
        tenant_id=row.tenant_id,
        title=row.title,
        description=row.description,
        suggested_activities=row.suggested_activities_json or [],
        status=row.status,
        progress_notes=row.progress_notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def update_career_goal(
    session: Session, ctx: OrganisationContext, goal_id: uuid.UUID, data: CareerGoalWrite
) -> CareerGoalOut:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(TenantCareerGoal, goal_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Career goal not found")
    if data.status not in {"pending", "in_progress", "completed"}:
        raise HTTPException(status_code=422, detail="Invalid status")
    row.title = data.title.strip()
    row.description = data.description
    row.suggested_activities_json = data.suggested_activities or []
    row.status = data.status
    row.progress_notes = data.progress_notes
    session.add(row)
    session.flush()
    return CareerGoalOut(
        id=row.id,
        tenant_id=row.tenant_id,
        title=row.title,
        description=row.description,
        suggested_activities=row.suggested_activities_json or [],
        status=row.status,
        progress_notes=row.progress_notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def get_roadmap(session: Session, ctx: OrganisationContext) -> RoadmapOut:
    tenant = resolve_own_tenant(session, ctx)
    assessment = session.scalar(
        select(TenantSkillAssessment).where(
            TenantSkillAssessment.organisation_id == ctx.organisation_id,
            TenantSkillAssessment.tenant_id == tenant.id,
        )
    )
    goals = list_career_goals(session, ctx)["items"]
    skills = assessment.skills_json if assessment else []
    interests = assessment.career_interests_json if assessment else []
    skill_names = {str(s.get("name", "")).lower() for s in skills if isinstance(s, dict)}
    suggested_learning = [
        "Practise interview answers using the interview preparation checklist.",
        "Update your CV after adding new skills or volunteering.",
        "Record applications you make outside HMore so follow-ups are not missed.",
    ]
    skill_gaps: list[str] = []
    for interest in interests or []:
        text = str(interest).lower()
        if text and text not in skill_names and not any(text in name for name in skill_names):
            skill_gaps.append(f"Consider building skills related to: {interest}")
    if not skill_gaps and not skills:
        skill_gaps.append("Add skills from education, volunteering or transferable experience.")
    return RoadmapOut(
        current_skills=skills or [],
        career_interests=interests or [],
        employment_goals=assessment.employment_goals if assessment else None,
        skill_gaps=skill_gaps,
        suggested_learning=suggested_learning,
        goals=goals,
    )


def upsert_interview_note(session: Session, ctx: OrganisationContext, data: InterviewNoteWrite) -> InterviewNoteOut:
    tenant = resolve_own_tenant(session, ctx)
    if data.application_id:
        app = session.get(TenantJobApplication, data.application_id)
        if app is None or app.tenant_id != tenant.id:
            raise HTTPException(status_code=404, detail="Application not found")
    row = TenantInterviewNote(
        organisation_id=ctx.organisation_id,
        tenant_id=tenant.id,
        application_id=data.application_id,
        interview_at=data.interview_at,
        notes=data.notes,
        questions_to_ask=data.questions_to_ask,
        checklist_json=data.checklist or [dict(item) for item in INTERVIEW_CHECKLIST_DEFAULT],
    )
    session.add(row)
    session.flush()
    return InterviewNoteOut(
        id=row.id,
        tenant_id=row.tenant_id,
        application_id=row.application_id,
        interview_at=row.interview_at,
        notes=row.notes,
        questions_to_ask=row.questions_to_ask,
        checklist=row.checklist_json or [],
        common_questions=list(COMMON_INTERVIEW_QUESTIONS),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_interview_notes(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    tenant = resolve_own_tenant(session, ctx)
    rows = list(
        session.scalars(
            select(TenantInterviewNote)
            .where(
                TenantInterviewNote.organisation_id == ctx.organisation_id,
                TenantInterviewNote.tenant_id == tenant.id,
            )
            .order_by(TenantInterviewNote.updated_at.desc())
        )
    )
    return {
        "common_questions": list(COMMON_INTERVIEW_QUESTIONS),
        "items": [
            InterviewNoteOut(
                id=row.id,
                tenant_id=row.tenant_id,
                application_id=row.application_id,
                interview_at=row.interview_at,
                notes=row.notes,
                questions_to_ask=row.questions_to_ask,
                checklist=row.checklist_json or [],
                common_questions=list(COMMON_INTERVIEW_QUESTIONS),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ],
    }


def staff_employment_summary(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID
) -> StaffEmploymentSummary:
    tenant = resolve_tenant_for_staff_or_self(session, ctx, tenant_id=tenant_id)
    assessment = session.scalar(
        select(TenantSkillAssessment).where(
            TenantSkillAssessment.organisation_id == ctx.organisation_id,
            TenantSkillAssessment.tenant_id == tenant.id,
        )
    )
    cv_count = session.scalar(
        select(func.count()).select_from(TenantCv).where(
            TenantCv.organisation_id == ctx.organisation_id, TenantCv.tenant_id == tenant.id
        )
    ) or 0
    app_count = session.scalar(
        select(func.count()).select_from(TenantJobApplication).where(
            TenantJobApplication.organisation_id == ctx.organisation_id,
            TenantJobApplication.tenant_id == tenant.id,
        )
    ) or 0
    open_goals = session.scalar(
        select(func.count()).select_from(TenantCareerGoal).where(
            TenantCareerGoal.organisation_id == ctx.organisation_id,
            TenantCareerGoal.tenant_id == tenant.id,
            TenantCareerGoal.status != "completed",
        )
    ) or 0
    skill_names = []
    if assessment:
        skill_names = [
            str(item.get("name"))
            for item in (assessment.skills_json or [])
            if isinstance(item, dict) and item.get("name")
        ]
    goals = list(
        session.scalars(
            select(TenantCareerGoal)
            .where(
                TenantCareerGoal.organisation_id == ctx.organisation_id,
                TenantCareerGoal.tenant_id == tenant.id,
            )
            .order_by(TenantCareerGoal.updated_at.desc())
            .limit(20)
        )
    )
    return StaffEmploymentSummary(
        tenant_id=tenant.id,
        assessment_status=assessment.status if assessment else None,
        completion_percent=assessment.completion_percent if assessment else None,
        cv_count=int(cv_count),
        application_count=int(app_count),
        open_goals=int(open_goals),
        skill_names=skill_names[:50],
        staff_support_notes=assessment.staff_support_notes if assessment else None,
        career_goals=[row.title for row in goals],
    )


def update_staff_support_notes(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID, notes: str
) -> StaffEmploymentSummary:
    """Authorised staff only — does not expose private CV or application detail."""
    if ctx.role == HMoreRole.TENANT:
        raise HTTPException(status_code=403, detail="Staff role required")
    tenant = resolve_tenant_for_staff_or_self(session, ctx, tenant_id=tenant_id)
    row = session.scalar(
        select(TenantSkillAssessment).where(
            TenantSkillAssessment.organisation_id == ctx.organisation_id,
            TenantSkillAssessment.tenant_id == tenant.id,
        )
    )
    if row is None:
        row = TenantSkillAssessment(
            organisation_id=ctx.organisation_id,
            tenant_id=tenant.id,
            skills_json=[],
            experiences_json=[],
            education_json=[],
            qualifications_json=[],
            certificates_json=[],
            languages_json=[],
            career_interests_json=[],
            preferred_work_types_json=[],
            status="in_progress",
            completion_percent=0,
        )
        session.add(row)
        session.flush()
    row.staff_support_notes = notes.strip()
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.EMPLOYMENT_ASSESSMENT_UPSERT,
        resource_type="tenant_skill_assessment",
        resource_id=row.id,
        summary="Staff employment support notes updated",
    )
    return staff_employment_summary(session, ctx, tenant.id)
