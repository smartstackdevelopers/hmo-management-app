"""F5.4 job search, matching, training and tracker integration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.catalogue import OpportunityListing
from app.db.models.employment import TenantCareerGoal, TenantCv, TenantJobApplication, TenantSkillAssessment
from app.db.models.enums import HMoreRole
from app.db.models.job_matching import (
    JobListing,
    TenantJobMatch,
    TenantJobMatchPreferences,
    TenantSavedJob,
    TenantSavedTraining,
    TrainingOpportunity,
)
from app.employment.access import resolve_own_tenant, resolve_tenant_for_staff_or_self
from app.employment.constants import APPLICATION_STATUSES
from app.employment.schemas import ApplicationCreate
from app.employment import service as employment_service
from app.job_matching.constants import SCORE_DISCLAIMER, SOURCE_CATALOGUE, SOURCE_STRUCTURED_IMPORT
from app.job_matching.embeddings import embed_text
from app.job_matching.schemas import (
    AddToTrackerRequest,
    JobListingOut,
    JobSearchResponse,
    MatchExplainRequest,
    MatchExplainResponse,
    MatchingProfileOut,
    PreferencesOut,
    PreferencesUpdate,
    StaffMatchProgress,
    StructuredJobImportBatch,
    StructuredTrainingImport,
    TrainingOut,
)
from app.job_matching.scoring import build_tenant_profile_text, score_job
from app.job_matching.sources import NormalizedJob, search_adzuna, search_reed, source_status
from app.job_matching import ai_client
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def _audit(session: Session, ctx: OrganisationContext, *, action: str, resource_type: str, resource_id, summary: str) -> None:
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
        raise_on_error=False,
    )


def _job_out(row: JobListing, match: dict[str, Any] | None = None) -> JobListingOut:
    base = JobListingOut(
        id=row.id,
        title=row.title,
        employer_name=row.employer_name,
        description=row.description,
        location=row.location,
        employment_type=row.employment_type,
        salary_text=row.salary_text,
        required_skills=row.required_skills_json or [],
        required_qualifications=row.required_qualifications_json or [],
        experience_requirements=row.experience_requirements,
        source_name=row.source_name,
        source_url=row.source_url,
        published_at=row.published_at,
        expires_at=row.expires_at,
        is_active=row.is_active,
        disclaimer=SCORE_DISCLAIMER,
    )
    if match:
        base.score = match.get("score")
        base.matching_skills = match.get("matching_skills")
        base.missing_skills = match.get("missing_skills")
        base.reasons = match.get("reasons")
    return base


def list_sources(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return {"sources": source_status(settings)}


def _load_assessment(session: Session, organisation_id: uuid.UUID, tenant_id: uuid.UUID) -> TenantSkillAssessment | None:
    return session.scalar(
        select(TenantSkillAssessment).where(
            TenantSkillAssessment.organisation_id == organisation_id,
            TenantSkillAssessment.tenant_id == tenant_id,
        )
    )


def _load_prefs(session: Session, organisation_id: uuid.UUID, tenant_id: uuid.UUID) -> TenantJobMatchPreferences | None:
    return session.scalar(
        select(TenantJobMatchPreferences).where(
            TenantJobMatchPreferences.organisation_id == organisation_id,
            TenantJobMatchPreferences.tenant_id == tenant_id,
        )
    )


def get_matching_profile(session: Session, ctx: OrganisationContext) -> MatchingProfileOut:
    tenant = resolve_own_tenant(session, ctx)
    assessment = _load_assessment(session, ctx.organisation_id, tenant.id)
    prefs = _load_prefs(session, ctx.organisation_id, tenant.id)
    cv = None
    if prefs and prefs.selected_cv_id:
        cv = session.get(TenantCv, prefs.selected_cv_id)
        if cv is None or cv.tenant_id != tenant.id:
            cv = None
    if cv is None:
        cv = session.scalar(
            select(TenantCv)
            .where(TenantCv.organisation_id == ctx.organisation_id, TenantCv.tenant_id == tenant.id, TenantCv.is_default.is_(True))
            .limit(1)
        )
    cv_skills = []
    cv_title = None
    if cv:
        cv_title = cv.title
        content = cv.content_json or {}
        cv_skills = content.get("skills") or []
    return MatchingProfileOut(
        tenant_id=tenant.id,
        skills=(assessment.skills_json if assessment else []) or [],
        experiences=(assessment.experiences_json if assessment else []) or [],
        education=(assessment.education_json if assessment else []) or [],
        qualifications=(assessment.qualifications_json if assessment else []) or [],
        certificates=(assessment.certificates_json if assessment else []) or [],
        languages=(assessment.languages_json if assessment else []) or [],
        career_interests=(assessment.career_interests_json if assessment else []) or [],
        preferred_work_types=(assessment.preferred_work_types_json if assessment else []) or [],
        employment_goals=assessment.employment_goals if assessment else None,
        selected_cv_id=cv.id if cv else None,
        cv_skills=cv_skills if isinstance(cv_skills, list) else [],
        cv_title=cv_title,
        assessment_completion_percent=int(assessment.completion_percent) if assessment else 0,
        note="Only your saved assessment and selected CV are used. Update skills via F5.3 Skills Assessment.",
    )


def _profile_dict(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    profile = get_matching_profile(session, ctx)
    prefs = get_preferences(session, ctx)
    return {
        "skills": profile.skills,
        "cv_skills": profile.cv_skills,
        "career_interests": list(profile.career_interests) + list(prefs.career_interests),
        "employment_goals": profile.employment_goals,
        "qualifications": profile.qualifications,
        "preferred_categories": prefs.preferred_categories,
        "preferred_locations": prefs.preferred_locations,
        "preferred_employment_types": prefs.preferred_employment_types or list(profile.preferred_work_types),
        "selected_cv_id": profile.selected_cv_id,
    }


def get_preferences(session: Session, ctx: OrganisationContext) -> PreferencesOut:
    tenant = resolve_own_tenant(session, ctx)
    row = _load_prefs(session, ctx.organisation_id, tenant.id)
    if row is None:
        return PreferencesOut(
            preferred_categories=[],
            preferred_locations=[],
            preferred_employment_types=[],
            preferred_experience_levels=[],
            career_interests=[],
            preferred_hours=None,
            salary_min=None,
            salary_max=None,
            selected_cv_id=None,
        )
    return PreferencesOut(
        preferred_categories=list(row.preferred_categories_json or []),
        preferred_locations=list(row.preferred_locations_json or []),
        preferred_employment_types=list(row.preferred_employment_types_json or []),
        preferred_experience_levels=list(row.preferred_experience_levels_json or []),
        career_interests=list(row.career_interests_json or []),
        preferred_hours=row.preferred_hours,
        salary_min=row.salary_min,
        salary_max=row.salary_max,
        selected_cv_id=row.selected_cv_id,
    )


def update_preferences(session: Session, ctx: OrganisationContext, data: PreferencesUpdate) -> PreferencesOut:
    tenant = resolve_own_tenant(session, ctx)
    row = _load_prefs(session, ctx.organisation_id, tenant.id)
    if row is None:
        row = TenantJobMatchPreferences(organisation_id=ctx.organisation_id, tenant_id=tenant.id)
        session.add(row)
        session.flush()
    if data.reset:
        row.preferred_categories_json = []
        row.preferred_locations_json = []
        row.preferred_employment_types_json = []
        row.preferred_experience_levels_json = []
        row.career_interests_json = []
        row.preferred_hours = None
        row.salary_min = None
        row.salary_max = None
        row.selected_cv_id = None
    else:
        payload = data.model_dump(exclude_unset=True, exclude={"reset"})
        if "selected_cv_id" in payload and payload["selected_cv_id"] is not None:
            cv = session.get(TenantCv, payload["selected_cv_id"])
            if cv is None or cv.tenant_id != tenant.id or cv.organisation_id != ctx.organisation_id:
                raise HTTPException(status_code=404, detail="CV not found")
        mapping = {
            "preferred_categories": "preferred_categories_json",
            "preferred_locations": "preferred_locations_json",
            "preferred_employment_types": "preferred_employment_types_json",
            "preferred_experience_levels": "preferred_experience_levels_json",
            "career_interests": "career_interests_json",
            "preferred_hours": "preferred_hours",
            "salary_min": "salary_min",
            "salary_max": "salary_max",
            "selected_cv_id": "selected_cv_id",
        }
        for key, attr in mapping.items():
            if key in payload:
                setattr(row, attr, payload[key])
    session.add(row)
    session.flush()
    _audit(session, ctx, action=audit_events.JOB_MATCH_PREFERENCES_UPDATE, resource_type="tenant_job_match_preferences", resource_id=row.id, summary="Job match preferences updated")
    return get_preferences(session, ctx)


def _upsert_normalized_job(session: Session, organisation_id: uuid.UUID, job: NormalizedJob) -> JobListing:
    fields = job.to_persist_fields()
    existing = session.scalar(
        select(JobListing).where(
            JobListing.organisation_id == organisation_id,
            JobListing.source_name == job.source_name,
            JobListing.external_id == job.external_id,
        )
    )
    now = datetime.now(timezone.utc)
    if existing and existing.expires_at and existing.expires_at < now:
        existing.is_active = False
    if existing is None:
        row = JobListing(organisation_id=organisation_id, **fields)
        session.add(row)
        session.flush()
        return row
    if existing.content_hash == fields["content_hash"]:
        existing.last_checked_at = now
        existing.is_active = True if (existing.expires_at is None or existing.expires_at >= now) else False
        session.add(existing)
        session.flush()
        return existing
    for key, value in fields.items():
        setattr(existing, key, value)
    session.add(existing)
    session.flush()
    return existing


def sync_catalogue_jobs(session: Session, ctx: OrganisationContext) -> int:
    """Pull published OpportunityListing jobs into searchable job_listings."""
    rows = list(
        session.scalars(
            select(OpportunityListing).where(
                OpportunityListing.organisation_id == ctx.organisation_id,
                OpportunityListing.kind == "job",
                OpportunityListing.is_published.is_(True),
            )
        )
    )
    count = 0
    for row in rows:
        job = NormalizedJob(
            external_id=str(row.id),
            source_name=SOURCE_CATALOGUE,
            source_url=row.source_url,
            title=row.title,
            employer_name=(row.source_name or "Organisation listing").strip() or "Organisation listing",
            description=row.description,
            location=None,
            employment_type=None,
            salary_text=None,
            required_skills=[],
            required_qualifications=[],
            experience_requirements=row.eligibility,
            published_at=None,
            expires_at=None,
        )
        _upsert_normalized_job(session, ctx.organisation_id, job)
        count += 1
    return count


def sync_catalogue_training(session: Session, ctx: OrganisationContext) -> int:
    rows = list(
        session.scalars(
            select(OpportunityListing).where(
                OpportunityListing.organisation_id == ctx.organisation_id,
                OpportunityListing.kind == "training",
                OpportunityListing.is_published.is_(True),
            )
        )
    )
    count = 0
    for row in rows:
        existing = session.scalar(
            select(TrainingOpportunity).where(
                TrainingOpportunity.organisation_id == ctx.organisation_id,
                TrainingOpportunity.source_name == SOURCE_CATALOGUE,
                TrainingOpportunity.external_id == str(row.id),
            )
        )
        if existing is None:
            existing = TrainingOpportunity(
                organisation_id=ctx.organisation_id,
                external_id=str(row.id),
                source_name=SOURCE_CATALOGUE,
                provider_name=(row.source_name or "Organisation training").strip() or "Organisation training",
                title=row.title,
            )
            session.add(existing)
        existing.description = row.description
        existing.eligibility = row.eligibility
        existing.source_url = row.source_url
        existing.is_active = True
        existing.verification_status = "verified"
        count += 1
    session.flush()
    return count


def import_structured_jobs(session: Session, ctx: OrganisationContext, batch: StructuredJobImportBatch) -> dict[str, int]:
    if not (
        ctx.authorization.has_permission(Permission.TENANTS_MANAGE)
        or ctx.authorization.has_permission(Permission.EMPLOYMENT_SUPPORT_MANAGE_ASSIGNED)
        or ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}
    ):
        raise HTTPException(status_code=403, detail="Staff import permission required")
    imported = 0
    for item in batch.jobs:
        if item.expires_at and item.expires_at < datetime.now(timezone.utc):
            continue
        job = NormalizedJob(
            external_id=item.external_id,
            source_name=SOURCE_STRUCTURED_IMPORT,
            source_url=item.source_url,
            title=item.title,
            employer_name=item.employer_name,
            description=item.description,
            location=item.location,
            employment_type=item.employment_type,
            salary_text=item.salary_text,
            required_skills=item.required_skills,
            required_qualifications=item.required_qualifications,
            experience_requirements=item.experience_requirements,
            published_at=item.published_at,
            expires_at=item.expires_at,
        )
        _upsert_normalized_job(session, ctx.organisation_id, job)
        imported += 1
    return {"imported": imported}


def import_structured_training(session: Session, ctx: OrganisationContext, item: StructuredTrainingImport) -> TrainingOut:
    if not (
        ctx.authorization.has_permission(Permission.TENANTS_MANAGE)
        or ctx.authorization.has_permission(Permission.EMPLOYMENT_SUPPORT_MANAGE_ASSIGNED)
        or ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}
    ):
        raise HTTPException(status_code=403, detail="Staff import permission required")
    if item.is_free_verified and item.verification_status != "verified":
        raise HTTPException(status_code=422, detail="Free courses must be verification_status=verified")
    row = session.scalar(
        select(TrainingOpportunity).where(
            TrainingOpportunity.organisation_id == ctx.organisation_id,
            TrainingOpportunity.source_name == SOURCE_STRUCTURED_IMPORT,
            TrainingOpportunity.external_id == item.external_id,
        )
    )
    if row is None:
        row = TrainingOpportunity(
            organisation_id=ctx.organisation_id,
            external_id=item.external_id,
            source_name=SOURCE_STRUCTURED_IMPORT,
            provider_name=item.provider_name,
            title=item.title,
        )
        session.add(row)
    row.provider_name = item.provider_name
    row.title = item.title
    row.description = item.description
    row.eligibility = item.eligibility
    row.duration = item.duration
    row.cost_text = item.cost_text
    row.is_free_verified = bool(item.is_free_verified and item.verification_status == "verified")
    row.source_url = item.source_url
    row.related_skills_json = item.related_skills
    row.verification_status = item.verification_status
    row.is_active = True
    session.flush()
    return TrainingOut(
        id=row.id,
        provider_name=row.provider_name,
        title=row.title,
        description=row.description,
        eligibility=row.eligibility,
        duration=row.duration,
        cost_text=row.cost_text,
        is_free_verified=row.is_free_verified,
        source_name=row.source_name,
        source_url=row.source_url,
        related_skills=row.related_skills_json or [],
        verification_status=row.verification_status,
    )


def _expire_stale(session: Session, organisation_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    rows = list(
        session.scalars(
            select(JobListing).where(
                JobListing.organisation_id == organisation_id,
                JobListing.is_active.is_(True),
                JobListing.expires_at.is_not(None),
                JobListing.expires_at < now,
            )
        )
    )
    for row in rows:
        row.is_active = False
        session.add(row)
    if rows:
        session.flush()


def search_jobs(
    session: Session,
    ctx: OrganisationContext,
    *,
    q: str | None,
    employer: str | None,
    location: str | None,
    employment_type: str | None,
    skills: str | None,
    sort: str,
    page: int,
    page_size: int,
    refresh_live: bool,
    settings: Settings | None = None,
) -> JobSearchResponse:
    resolve_own_tenant(session, ctx)
    settings = settings or get_settings()
    _expire_stale(session, ctx.organisation_id)
    sync_catalogue_jobs(session, ctx)

    sources_meta = source_status(settings)
    unavailable = [s for s in sources_meta if not s["available"] and s["source"] in {"adzuna", "reed"}]
    used: list[str] = [SOURCE_CATALOGUE]

    if refresh_live and settings.job_match_live_search_enabled:
        query_text = q or skills
        adzuna_jobs = search_adzuna(settings, what=query_text, where=location, page=1, results_per_page=min(page_size, 25))
        for job in adzuna_jobs:
            _upsert_normalized_job(session, ctx.organisation_id, job)
        if adzuna_jobs:
            used.append("adzuna")
        reed_jobs = search_reed(settings, keywords=query_text, location=location, results_to_take=min(page_size, 25))
        for job in reed_jobs:
            _upsert_normalized_job(session, ctx.organisation_id, job)
        if reed_jobs:
            used.append("reed")

    stmt = select(JobListing).where(
        JobListing.organisation_id == ctx.organisation_id,
        JobListing.is_active.is_(True),
    )
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                JobListing.title.ilike(pattern),
                JobListing.description.ilike(pattern),
                JobListing.search_document.ilike(pattern),
            )
        )
    if employer:
        stmt = stmt.where(JobListing.employer_name.ilike(f"%{employer.strip()}%"))
    if location:
        stmt = stmt.where(JobListing.location.ilike(f"%{location.strip()}%"))
    if employment_type:
        stmt = stmt.where(JobListing.employment_type == employment_type)
    if skills:
        for token in [t.strip() for t in skills.split(",") if t.strip()][:5]:
            stmt = stmt.where(JobListing.search_document.ilike(f"%{token}%"))

    if sort == "published_at":
        stmt = stmt.order_by(JobListing.published_at.desc().nullslast(), JobListing.updated_at.desc())
    else:
        stmt = stmt.order_by(JobListing.updated_at.desc())

    rows = list(session.scalars(stmt.limit(200)))
    profile = _profile_dict(session, ctx)
    profile_embedding = embed_text(build_tenant_profile_text(profile))

    scored: list[tuple[JobListing, dict[str, Any]]] = []
    for row in rows:
        match = score_job(
            profile=profile,
            job={
                "title": row.title,
                "description": row.description,
                "location": row.location,
                "employment_type": row.employment_type,
                "required_skills": row.required_skills_json or [],
                "embedding": row.embedding_json or [],
            },
            profile_embedding=profile_embedding,
        )
        scored.append((row, match))
        _persist_match(session, ctx, row, match, profile.get("selected_cv_id"))

    if sort != "published_at":
        scored.sort(key=lambda item: item[1]["score"], reverse=True)

    page = max(1, page)
    page_size = min(50, max(1, page_size))
    start = (page - 1) * page_size
    slice_rows = scored[start : start + page_size]
    return JobSearchResponse(
        items=[_job_out(row, match) for row, match in slice_rows],
        total=len(scored),
        page=page,
        page_size=page_size,
        sources_used=used,
        sources_unavailable=unavailable,
        ai_used=False,
        disclaimer=SCORE_DISCLAIMER,
    )


def _persist_match(
    session: Session,
    ctx: OrganisationContext,
    job: JobListing,
    match: dict[str, Any],
    cv_id: uuid.UUID | None,
) -> None:
    tenant = resolve_own_tenant(session, ctx)
    row = session.scalar(
        select(TenantJobMatch).where(
            TenantJobMatch.tenant_id == tenant.id,
            TenantJobMatch.job_id == job.id,
        )
    )
    if row is None:
        row = TenantJobMatch(
            organisation_id=ctx.organisation_id,
            tenant_id=tenant.id,
            job_id=job.id,
            score=float(match["score"]),
        )
        session.add(row)
    row.score = float(match["score"])
    row.reasons_json = match.get("reasons") or []
    row.matching_skills_json = match.get("matching_skills") or []
    row.missing_skills_json = match.get("missing_skills") or []
    row.cv_id = cv_id
    session.flush()


def get_job(session: Session, ctx: OrganisationContext, job_id: uuid.UUID) -> JobListingOut:
    resolve_own_tenant(session, ctx)
    row = session.get(JobListing, job_id)
    if row is None or row.organisation_id != ctx.organisation_id or not row.is_active:
        raise HTTPException(status_code=404, detail="Job not found")
    profile = _profile_dict(session, ctx)
    match = score_job(
        profile=profile,
        job={
            "title": row.title,
            "description": row.description,
            "location": row.location,
            "employment_type": row.employment_type,
            "required_skills": row.required_skills_json or [],
            "embedding": row.embedding_json or [],
        },
        profile_embedding=embed_text(build_tenant_profile_text(profile)),
    )
    return _job_out(row, match)


def recommend_jobs(session: Session, ctx: OrganisationContext, *, limit: int = 20) -> JobSearchResponse:
    prefs = get_preferences(session, ctx)
    q = " ".join(prefs.preferred_categories[:3] + prefs.career_interests[:3]) or None
    location = prefs.preferred_locations[0] if prefs.preferred_locations else None
    employment_type = prefs.preferred_employment_types[0] if prefs.preferred_employment_types else None
    return search_jobs(
        session,
        ctx,
        q=q,
        employer=None,
        location=location,
        employment_type=employment_type,
        skills=None,
        sort="relevance",
        page=1,
        page_size=limit,
        refresh_live=True,
    )


def save_job(session: Session, ctx: OrganisationContext, job_id: uuid.UUID) -> dict[str, str]:
    tenant = resolve_own_tenant(session, ctx)
    job = session.get(JobListing, job_id)
    if job is None or job.organisation_id != ctx.organisation_id or not job.is_active:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = session.scalar(
        select(TenantSavedJob).where(TenantSavedJob.tenant_id == tenant.id, TenantSavedJob.job_id == job_id)
    )
    if existing:
        return {"status": "already_saved"}
    session.add(
        TenantSavedJob(organisation_id=ctx.organisation_id, tenant_id=tenant.id, job_id=job_id)
    )
    session.flush()
    _audit(session, ctx, action=audit_events.JOB_MATCH_SAVE, resource_type="tenant_saved_job", resource_id=job_id, summary="Job saved")
    return {"status": "saved"}


def unsave_job(session: Session, ctx: OrganisationContext, job_id: uuid.UUID) -> dict[str, str]:
    tenant = resolve_own_tenant(session, ctx)
    row = session.scalar(
        select(TenantSavedJob).where(TenantSavedJob.tenant_id == tenant.id, TenantSavedJob.job_id == job_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Saved job not found")
    session.delete(row)
    session.flush()
    return {"status": "removed"}


def list_saved_jobs(session: Session, ctx: OrganisationContext) -> dict[str, list[JobListingOut]]:
    tenant = resolve_own_tenant(session, ctx)
    rows = list(
        session.scalars(
            select(JobListing)
            .join(TenantSavedJob, TenantSavedJob.job_id == JobListing.id)
            .where(TenantSavedJob.tenant_id == tenant.id, JobListing.organisation_id == ctx.organisation_id)
            .order_by(TenantSavedJob.created_at.desc())
        )
    )
    return {"items": [_job_out(row) for row in rows]}


def recommend_training(session: Session, ctx: OrganisationContext) -> dict[str, list[TrainingOut]]:
    resolve_own_tenant(session, ctx)
    sync_catalogue_training(session, ctx)
    profile = _profile_dict(session, ctx)
    goals = list(
        session.scalars(
            select(TenantCareerGoal).where(
                TenantCareerGoal.organisation_id == ctx.organisation_id,
                TenantCareerGoal.tenant_id == resolve_own_tenant(session, ctx).id,
            )
        )
    )
    goal_text = " ".join([g.title for g in goals] + [str(profile.get("employment_goals") or "")]).lower()
    skill_names = {
        str(s.get("name") or "").lower()
        for s in (profile.get("skills") or []) + (profile.get("cv_skills") or [])
        if isinstance(s, dict)
    }
    rows = list(
        session.scalars(
            select(TrainingOpportunity).where(
                TrainingOpportunity.organisation_id == ctx.organisation_id,
                TrainingOpportunity.is_active.is_(True),
            )
        )
    )
    items: list[TrainingOut] = []
    for row in rows:
        related = [str(s).lower() for s in (row.related_skills_json or [])]
        reasons = []
        if any(s and s in goal_text for s in related):
            reasons.append("Related to your career goals")
        if related and skill_names and not (set(related) & skill_names):
            reasons.append("May help address skill gaps for your goals")
        if not reasons and (goal_text and any(tok in (row.title or "").lower() for tok in goal_text.split() if len(tok) > 3)):
            reasons.append("Title overlaps with your goals")
        if not reasons:
            continue
        items.append(
            TrainingOut(
                id=row.id,
                provider_name=row.provider_name,
                title=row.title,
                description=row.description,
                eligibility=row.eligibility,
                duration=row.duration,
                cost_text=row.cost_text,
                is_free_verified=row.is_free_verified,
                source_name=row.source_name,
                source_url=row.source_url,
                related_skills=row.related_skills_json or [],
                verification_status=row.verification_status,
                reasons=reasons,
            )
        )
    return {"items": items, "disclaimer": "Training suggestions are not enrolment. Free status only when verified."}


def save_training(session: Session, ctx: OrganisationContext, training_id: uuid.UUID) -> dict[str, str]:
    tenant = resolve_own_tenant(session, ctx)
    row = session.get(TrainingOpportunity, training_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Training not found")
    existing = session.scalar(
        select(TenantSavedTraining).where(
            TenantSavedTraining.tenant_id == tenant.id, TenantSavedTraining.training_id == training_id
        )
    )
    if existing:
        return {"status": "already_saved"}
    session.add(
        TenantSavedTraining(organisation_id=ctx.organisation_id, tenant_id=tenant.id, training_id=training_id)
    )
    session.flush()
    return {"status": "saved"}


def mark_training_status(
    session: Session, ctx: OrganisationContext, training_id: uuid.UUID, status_value: str
) -> dict[str, str]:
    if status_value not in {"saved", "in_progress", "completed"}:
        raise HTTPException(status_code=422, detail="Invalid status")
    tenant = resolve_own_tenant(session, ctx)
    row = session.scalar(
        select(TenantSavedTraining).where(
            TenantSavedTraining.tenant_id == tenant.id, TenantSavedTraining.training_id == training_id
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Saved training not found")
    row.status = status_value
    session.add(row)
    session.flush()
    return {"status": status_value}


def add_job_to_tracker(session: Session, ctx: OrganisationContext, data: AddToTrackerRequest) -> dict[str, Any]:
    tenant = resolve_own_tenant(session, ctx)
    job = session.get(JobListing, data.job_id)
    if job is None or job.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Job not found")
    if data.status not in APPLICATION_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")
    if data.status == "applied":
        raise HTTPException(
            status_code=422,
            detail="Do not mark Applied until you confirm you submitted the application",
        )
    # Prevent duplicates by employer+title for active rows.
    dup = session.scalar(
        select(TenantJobApplication).where(
            TenantJobApplication.organisation_id == ctx.organisation_id,
            TenantJobApplication.tenant_id == tenant.id,
            TenantJobApplication.employer_name == job.employer_name,
            TenantJobApplication.job_title == job.title,
            TenantJobApplication.is_archived.is_(False),
        )
    )
    if dup is not None:
        return {"status": "already_tracked", "application_id": str(dup.id)}
    notes = data.notes or ""
    if job.source_url:
        notes = (notes + f"\nSource: {job.source_url}").strip()
    created = employment_service.create_application(
        session,
        ctx,
        ApplicationCreate(
            employer_name=job.employer_name,
            job_title=job.title,
            job_location=job.location,
            source=job.source_name,
            linked_cv_id=data.linked_cv_id,
            status=data.status,
            notes=notes or None,
        ),
    )
    _audit(session, ctx, action=audit_events.JOB_MATCH_TRACKER_ADD, resource_type="tenant_job_application", resource_id=created.id, summary="Matched job added to tracker")
    return {"status": "created", "application": created.model_dump(mode="json")}


def explain_match(session: Session, ctx: OrganisationContext, body: MatchExplainRequest) -> MatchExplainResponse:
    job = get_job(session, ctx, body.job_id)
    profile = get_matching_profile(session, ctx)
    profile_summary = {
        "skills": [s.get("name") for s in profile.skills if isinstance(s, dict)][:20],
        "career_interests": profile.career_interests[:10],
        "employment_goals": profile.employment_goals,
        "cv_title": profile.cv_title,
    }
    match = {
        "score": job.score,
        "matching_skills": job.matching_skills,
        "missing_skills": job.missing_skills,
        "reasons": job.reasons,
    }
    job_payload = {
        "title": job.title,
        "employer_name": job.employer_name,
        "location": job.location,
        "employment_type": job.employment_type,
        "salary_text": job.salary_text,
        "required_skills": job.required_skills,
        "source_name": job.source_name,
        "source_url": job.source_url,
        "description": (job.description or "")[:2000],
    }
    try:
        text = ai_client.explain_job_match(
            session,
            ctx,
            job=job_payload,
            profile_summary=profile_summary,
            match=match,
            question=body.question,
        )
        provider = "ai_service"
    except HTTPException as exc:
        if exc.status_code not in {402, 503}:
            raise
        # Deterministic fallback — no invented content.
        parts = [
            f"This listing is '{job.title}' at {job.employer_name} (source: {job.source_name}).",
            *(job.reasons or []),
        ]
        if job.missing_skills:
            parts.append(
                "Skills on the listing that are not yet on your profile: "
                + ", ".join(job.missing_skills[:8])
                + ". Update your F5.3 assessment if you have them."
            )
        parts.append("This is a suggestion only — not a guarantee of employment.")
        text = " ".join(parts)
        provider = "deterministic_fallback" if exc.status_code == 503 else "usage_limited_fallback"
        if exc.status_code == 402:
            provider = "usage_limited_fallback"
    return MatchExplainResponse(
        job_id=job.id,
        explanation=text,
        provider=provider,
        requires_review=True,
        disclaimer=SCORE_DISCLAIMER,
    )


def staff_match_progress(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> StaffMatchProgress:
    tenant = resolve_tenant_for_staff_or_self(session, ctx, tenant_id=tenant_id)
    saved = session.scalar(
        select(func.count()).select_from(TenantSavedJob).where(
            TenantSavedJob.organisation_id == ctx.organisation_id, TenantSavedJob.tenant_id == tenant.id
        )
    ) or 0
    matches = list(
        session.scalars(
            select(TenantJobMatch)
            .where(TenantJobMatch.organisation_id == ctx.organisation_id, TenantJobMatch.tenant_id == tenant.id)
            .order_by(TenantJobMatch.score.desc())
            .limit(10)
        )
    )
    goals = list(
        session.scalars(
            select(TenantCareerGoal).where(
                TenantCareerGoal.organisation_id == ctx.organisation_id,
                TenantCareerGoal.tenant_id == tenant.id,
            )
        )
    )
    prefs = _load_prefs(session, ctx.organisation_id, tenant.id)
    return StaffMatchProgress(
        tenant_id=tenant.id,
        saved_jobs=int(saved),
        match_count=len(matches),
        top_scores=[float(m.score) for m in matches[:5]],
        career_goals=[g.title for g in goals],
        preferred_categories=list(prefs.preferred_categories_json or []) if prefs else [],
    )
