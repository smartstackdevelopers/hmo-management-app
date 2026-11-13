"""F8.5 contractor marketplace service."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.contractor_marketplace import (
    ContractorDirectoryProfile,
    ContractorDocument,
    ContractorServiceCategory,
    ContractorVerificationReview,
    MarketplaceContractorFeedback,
    MarketplaceJob,
    MarketplaceJobCompletion,
    MarketplaceQuotation,
    OrganisationContractorMarketplaceSettings,
)
from app.db.models.enums import HMoreRole
from app.contractor_marketplace import access
from app.contractor_marketplace.constants import ADDON_DISCLAIMER, DEFAULT_CATEGORIES
from app.ops.notifications import ReminderMessage, get_notification_provider
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _settings(session: Session, org_id: UUID) -> OrganisationContractorMarketplaceSettings:
    row = session.scalars(
        select(OrganisationContractorMarketplaceSettings).where(
            OrganisationContractorMarketplaceSettings.organisation_id == org_id
        )
    ).first()
    if row is None:
        row = OrganisationContractorMarketplaceSettings(organisation_id=org_id)
        session.add(row)
        session.flush()
    return row


def assert_addon(session: Session, settings: Settings, org_id: UUID) -> OrganisationContractorMarketplaceSettings:
    if not settings.contractor_marketplace_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Contractor marketplace add-on disabled platform-wide")
    row = _settings(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Contractor marketplace disabled for organisation")
    return row


def update_settings(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> OrganisationContractorMarketplaceSettings:
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_MANAGE)
    row = assert_addon(session, get_settings(), ctx.organisation_id)
    if data.get("enabled") is not None:
        row.enabled = bool(data["enabled"])
    if data.get("privacy_review_complete") is not None:
        row.privacy_review_complete = bool(data["privacy_review_complete"])
    if data.get("show_contact_to_landlords") is not None:
        row.show_contact_to_landlords = bool(data["show_contact_to_landlords"])
    if data.get("reminder_config") is not None:
        row.reminder_config = data["reminder_config"]
    session.flush()
    record_event(
        session,
        action=audit_events.CONTRACTOR_MARKETPLACE_SETTINGS_UPDATE,
        resource_type="contractor_marketplace_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Contractor marketplace settings updated",
    )
    return row


def list_categories(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    access.require_read(ctx)
    ensure_categories(session, ctx.organisation_id)
    rows = session.scalars(
        select(ContractorServiceCategory)
        .where(ContractorServiceCategory.organisation_id == ctx.organisation_id)
        .order_by(ContractorServiceCategory.sort_order)
    ).all()
    return [{"slug": r.slug, "name": r.name, "active": r.active} for r in rows]


def settings_dict(row: OrganisationContractorMarketplaceSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "show_contact_to_landlords": row.show_contact_to_landlords,
        "reminder_config": row.reminder_config,
        "disclaimer": ADDON_DISCLAIMER,
    }


def ensure_categories(session: Session, org_id: UUID) -> None:
    if session.scalar(select(func.count()).select_from(ContractorServiceCategory).where(ContractorServiceCategory.organisation_id == org_id)):
        return
    for idx, (slug, name) in enumerate(DEFAULT_CATEGORIES):
        session.add(ContractorServiceCategory(organisation_id=org_id, slug=slug, name=name, is_system=True, sort_order=idx))
    session.flush()


def contractor_profile_for_user(session: Session, org_id: UUID, user_id: UUID) -> ContractorDirectoryProfile | None:
    return session.scalar(
        select(ContractorDirectoryProfile).where(
            ContractorDirectoryProfile.organisation_id == org_id,
            ContractorDirectoryProfile.contractor_user_id == user_id,
        )
    )


def submit_registration(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> ContractorDirectoryProfile:
    if ctx.role != HMoreRole.MAINTENANCE_CONTRACTOR and ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_REGISTER)
    assert_addon(session, get_settings(), ctx.organisation_id)
    profile = contractor_profile_for_user(session, ctx.organisation_id, ctx.user_id)
    if profile is None:
        profile = ContractorDirectoryProfile(
            organisation_id=ctx.organisation_id,
            contractor_user_id=ctx.user_id,
            business_name=data["business_name"],
            verification_status="draft",
        )
        session.add(profile)
    profile.business_description = data.get("business_description")
    profile.contact_email = data.get("contact_email")
    profile.contact_phone = data.get("contact_phone")
    profile.service_category_slugs = data.get("service_category_slugs") or []
    profile.operating_locations = data.get("operating_locations") or []
    profile.service_coverage = data.get("service_coverage")
    profile.availability_notes = data.get("availability_notes")
    profile.insurance_expiry = data.get("insurance_expiry")
    profile.verification_status = "submitted"
    session.flush()
    record_event(
        session,
        action=audit_events.CONTRACTOR_MARKETPLACE_REGISTERED,
        resource_type="contractor_profile",
        resource_id=str(profile.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Contractor registration submitted",
    )
    return profile


def review_contractor(
    session: Session,
    ctx: OrganisationContext,
    profile_id: UUID,
    *,
    decision: str,
    notes: str | None,
) -> ContractorDirectoryProfile:
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_MANAGE)
    profile = session.get(ContractorDirectoryProfile, profile_id)
    if profile is None or profile.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profile not found")
    session.add(
        ContractorVerificationReview(
            organisation_id=ctx.organisation_id,
            profile_id=profile.id,
            reviewer_user_id=ctx.user_id,
            decision=decision,
            notes=notes,
        )
    )
    if decision == "approve":
        profile.verification_status = "approved"
        profile.account_status = "active"
    elif decision == "reject":
        profile.verification_status = "rejected"
        profile.account_status = "inactive"
    elif decision == "suspend":
        profile.verification_status = "suspended"
        profile.account_status = "suspended"
    else:
        profile.verification_status = "under_review"
    session.flush()
    record_event(
        session,
        action=audit_events.CONTRACTOR_MARKETPLACE_VERIFIED,
        resource_type="contractor_profile",
        resource_id=str(profile.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Contractor verification decision: {decision}",
    )
    return profile


def search_marketplace(
    session: Session,
    ctx: OrganisationContext,
    *,
    category: str | None,
    location: str | None,
) -> list[dict[str, Any]]:
    access.require_read(ctx)
    settings = _settings(session, ctx.organisation_id)
    q = select(ContractorDirectoryProfile).where(
        ContractorDirectoryProfile.organisation_id == ctx.organisation_id,
        ContractorDirectoryProfile.verification_status == "approved",
        ContractorDirectoryProfile.account_status == "active",
    )
    rows = session.scalars(q).all()
    out: list[dict[str, Any]] = []
    for p in rows:
        if category and category not in (p.service_category_slugs or []):
            continue
        if location and location not in str(p.operating_locations):
            continue
        item = {
            "id": str(p.id),
            "business_name": p.business_name,
            "service_category_slugs": p.service_category_slugs,
            "service_coverage": p.service_coverage,
            "verification_status": p.verification_status,
        }
        if settings.show_contact_to_landlords and ctx.role in {
            HMoreRole.LANDLORD,
            HMoreRole.ORGANISATION_ADMIN,
            HMoreRole.SUPER_ADMIN,
        }:
            item["contact_email"] = p.contact_email
            item["contact_phone"] = p.contact_phone
        out.append(item)
    return out


def _next_job_ref(session: Session, org_id: UUID) -> str:
    year = _now().year
    prefix = f"MKT-{year}-"
    n = (
        session.scalar(
            select(func.count()).select_from(MarketplaceJob).where(
                MarketplaceJob.organisation_id == org_id,
                MarketplaceJob.reference_number.like(f"{prefix}%"),
            )
        )
        or 0
    )
    return f"{prefix}{n + 1:05d}"


def create_job(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> MarketplaceJob:
    access.require_manage(ctx)
    assert_addon(session, get_settings(), ctx.organisation_id)
    job = MarketplaceJob(
        organisation_id=ctx.organisation_id,
        reference_number=_next_job_ref(session, ctx.organisation_id),
        maintenance_request_id=data.get("maintenance_request_id"),
        property_id=data["property_id"],
        description=data["description"],
        priority=data.get("priority", "normal"),
        status="requested",
        preferred_start_date=data.get("preferred_start_date"),
        quotations_requested=bool(data.get("quotations_requested")),
        created_by_user_id=ctx.user_id,
    )
    if job.quotations_requested:
        job.status = "quotation_pending"
    session.add(job)
    ensure_categories(session, ctx.organisation_id)
    session.flush()
    record_event(
        session,
        action=audit_events.CONTRACTOR_MARKETPLACE_JOB_CREATED,
        resource_type="marketplace_job",
        resource_id=str(job.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Marketplace job created",
    )
    return job


def submit_quotation(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> MarketplaceQuotation:
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_QUOTE)
    profile = contractor_profile_for_user(session, ctx.organisation_id, ctx.user_id)
    if profile is None or profile.verification_status != "approved":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Approved contractor profile required")
    job = session.get(MarketplaceJob, data["job_id"])
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    ref = data.get("quotation_reference") or f"QT-{job.reference_number}-{uuid.uuid4().hex[:6]}"
    dup = session.scalar(
        select(MarketplaceQuotation).where(
            MarketplaceQuotation.organisation_id == ctx.organisation_id,
            MarketplaceQuotation.quotation_reference == ref,
        )
    )
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Duplicate quotation reference")
    labour = Decimal(str(data.get("labour_cost", 0)))
    material = Decimal(str(data.get("material_cost", 0)))
    extra = Decimal(str(data.get("additional_charges", 0)))
    tax = Decimal(str(data["tax_amount"])) if data.get("tax_amount") is not None else None
    total = Decimal(str(data.get("total_amount", labour + material + extra + (tax or 0))))
    quote = MarketplaceQuotation(
        organisation_id=ctx.organisation_id,
        job_id=job.id,
        contractor_profile_id=profile.id,
        quotation_reference=ref,
        labour_cost=labour,
        material_cost=material,
        additional_charges=extra,
        tax_amount=tax,
        total_amount=total,
        currency=data.get("currency", "GBP"),
        proposed_start_date=data.get("proposed_start_date"),
        estimated_completion_date=data.get("estimated_completion_date"),
        work_description=data.get("work_description"),
        valid_until=data.get("valid_until"),
    )
    session.add(quote)
    job.status = "quotation_received"
    session.flush()
    record_event(
        session,
        action=audit_events.CONTRACTOR_MARKETPLACE_QUOTE_SUBMITTED,
        resource_type="marketplace_quotation",
        resource_id=str(quote.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Marketplace quotation submitted",
    )
    _notify_user(session, ctx.organisation_id, job.created_by_user_id, "New quotation submitted")
    return quote


def approve_quotation(session: Session, ctx: OrganisationContext, quotation_id: UUID) -> MarketplaceQuotation:
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_APPROVE)
    quote = session.get(MarketplaceQuotation, quotation_id)
    if quote is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    quote.status = "approved"
    quote.approved_by_user_id = ctx.user_id
    job = session.get(MarketplaceJob, quote.job_id)
    if job and not job.assigned_contractor_profile_id:
        job.assigned_contractor_profile_id = quote.contractor_profile_id
        job.status = "assigned"
    session.flush()
    profile = session.get(ContractorDirectoryProfile, quote.contractor_profile_id)
    if profile:
        _notify_user(session, ctx.organisation_id, profile.contractor_user_id, "Quotation approved")
    return quote


def assign_job(session: Session, ctx: OrganisationContext, job_id: UUID, profile_id: UUID) -> MarketplaceJob:
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_APPROVE)
    job = session.get(MarketplaceJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.assigned_contractor_profile_id and job.assigned_contractor_profile_id != profile_id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Job already assigned")
    job.assigned_contractor_profile_id = profile_id
    job.status = "assigned"
    session.flush()
    record_event(
        session,
        action=audit_events.CONTRACTOR_MARKETPLACE_JOB_ASSIGNED,
        resource_type="marketplace_job",
        resource_id=str(job.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Marketplace job assigned to contractor",
    )
    profile = session.get(ContractorDirectoryProfile, profile_id)
    if profile:
        _notify_user(session, ctx.organisation_id, profile.contractor_user_id, "Job assigned")
    return job


def workspace_jobs(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    access.require_workspace(ctx)
    profile = contractor_profile_for_user(session, ctx.organisation_id, ctx.user_id)
    if profile is None:
        return []
    jobs = session.scalars(
        select(MarketplaceJob).where(
            MarketplaceJob.organisation_id == ctx.organisation_id,
            MarketplaceJob.assigned_contractor_profile_id == profile.id,
        )
    ).all()
    return [
        {"id": str(j.id), "reference_number": j.reference_number, "status": j.status, "description": j.description[:200]}
        for j in jobs
    ]


def submit_completion(session: Session, ctx: OrganisationContext, job_id: UUID, data: dict[str, Any]) -> MarketplaceJobCompletion:
    access.require_workspace(ctx)
    profile = contractor_profile_for_user(session, ctx.organisation_id, ctx.user_id)
    job = session.get(MarketplaceJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    access.assert_job_visible(ctx, job, profile)
    completion = MarketplaceJobCompletion(
        organisation_id=ctx.organisation_id,
        job_id=job.id,
        completion_notes=data.get("completion_notes"),
        completed_at=_now(),
        materials_used=data.get("materials_used"),
        outstanding_work=data.get("outstanding_work"),
        contractor_declaration=bool(data.get("contractor_declaration")),
    )
    session.add(completion)
    job.status = "completed"
    session.flush()
    record_event(
        session,
        action=audit_events.CONTRACTOR_MARKETPLACE_COMPLETION_SUBMITTED,
        resource_type="marketplace_job_completion",
        resource_id=str(completion.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Marketplace job completion submitted",
    )
    _notify_user(session, ctx.organisation_id, job.created_by_user_id, "Job completion submitted")
    return completion


def review_completion(
    session: Session, ctx: OrganisationContext, completion_id: UUID, *, review_status: str, review_notes: str | None
) -> MarketplaceJobCompletion:
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_APPROVE)
    completion = session.get(MarketplaceJobCompletion, completion_id)
    if completion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Completion not found")
    completion.review_status = review_status
    completion.review_notes = review_notes
    completion.reviewed_by_user_id = ctx.user_id
    job = session.get(MarketplaceJob, completion.job_id)
    if job and review_status == "approved":
        job.status = "verified"
    session.flush()
    return completion


def submit_feedback(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> MarketplaceContractorFeedback:
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_APPROVE)
    job = session.get(MarketplaceJob, data["job_id"])
    if job is None or job.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    feedback = MarketplaceContractorFeedback(
        organisation_id=ctx.organisation_id,
        job_id=job.id,
        reviewer_user_id=ctx.user_id,
        work_quality=data.get("work_quality"),
        timeliness=data.get("timeliness"),
        communication=data.get("communication"),
        professional_conduct=data.get("professional_conduct"),
        feedback_text=data.get("feedback_text"),
        moderation_status="pending",
    )
    session.add(feedback)
    session.flush()
    return feedback


def admin_dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_REPORTS)
    org = ctx.organisation_id
    contractors = session.scalar(select(func.count()).select_from(ContractorDirectoryProfile).where(ContractorDirectoryProfile.organisation_id == org)) or 0
    approved = (
        session.scalar(
            select(func.count()).select_from(ContractorDirectoryProfile).where(
                ContractorDirectoryProfile.organisation_id == org,
                ContractorDirectoryProfile.verification_status == "approved",
            )
        )
        or 0
    )
    pending = (
        session.scalar(
            select(func.count()).select_from(ContractorDirectoryProfile).where(
                ContractorDirectoryProfile.organisation_id == org,
                ContractorDirectoryProfile.verification_status.in_(("submitted", "under_review")),
            )
        )
        or 0
    )
    open_jobs = (
        session.scalar(
            select(func.count()).select_from(MarketplaceJob).where(
                MarketplaceJob.organisation_id == org,
                MarketplaceJob.status.notin_(("verified", "cancelled")),
            )
        )
        or 0
    )
    return {
        "contractors_total": int(contractors),
        "contractors_approved": int(approved),
        "pending_verification": int(pending),
        "open_jobs": int(open_jobs),
    }


def _notify_user(session: Session, org_id: UUID, user_id: UUID | None, subject: str) -> None:
    if user_id is None:
        return
    provider = get_notification_provider()
    provider.send(
        session,
        ReminderMessage(
            organisation_id=str(org_id),
            recipient_user_id=str(user_id),
            subject=subject,
            body="Open HMore for marketplace details.",
            channel="in_app",
            target_type="contractor_marketplace",
            target_id=subject[:40],
            idempotency_key=f"cm:{user_id}:{subject}:{date.today().isoformat()}",
            essential_operational=True,
        ),
    )
