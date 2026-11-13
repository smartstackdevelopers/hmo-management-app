"""F8.5 optional contractor marketplace API."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.contractor_marketplace import service
from app.contractor_marketplace.service import _settings
from app.db.session import get_session
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/contractor-marketplace", tags=["contractor-marketplace"])


class SettingsBody(BaseModel):
    enabled: bool | None = None
    privacy_review_complete: bool | None = None
    show_contact_to_landlords: bool | None = None
    reminder_config: dict[str, Any] | None = None


class RegistrationBody(BaseModel):
    business_name: str = Field(min_length=1, max_length=255)
    business_description: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    service_category_slugs: list[str] = Field(default_factory=list)
    operating_locations: list[str] = Field(default_factory=list)
    service_coverage: str | None = None
    availability_notes: str | None = None
    insurance_expiry: date | None = None


class VerificationBody(BaseModel):
    decision: str = Field(pattern="^(approve|reject|request_evidence|suspend)$")
    notes: str | None = None


class JobBody(BaseModel):
    property_id: uuid.UUID
    description: str = Field(min_length=1)
    maintenance_request_id: uuid.UUID | None = None
    priority: str = "normal"
    preferred_start_date: date | None = None
    quotations_requested: bool = False


class QuotationBody(BaseModel):
    job_id: uuid.UUID
    quotation_reference: str | None = None
    labour_cost: Decimal = Decimal("0")
    material_cost: Decimal = Decimal("0")
    additional_charges: Decimal = Decimal("0")
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    currency: str = "GBP"
    proposed_start_date: date | None = None
    estimated_completion_date: date | None = None
    work_description: str | None = None
    valid_until: date | None = None


class CompletionBody(BaseModel):
    completion_notes: str | None = None
    materials_used: str | None = None
    outstanding_work: str | None = None
    contractor_declaration: bool = False


class CompletionReviewBody(BaseModel):
    review_status: str = Field(pattern="^(approved|rejected|additional_work_required)$")
    review_notes: str | None = None


class FeedbackBody(BaseModel):
    job_id: uuid.UUID
    work_quality: int | None = Field(default=None, ge=1, le=5)
    timeliness: int | None = Field(default=None, ge=1, le=5)
    communication: int | None = Field(default=None, ge=1, le=5)
    professional_conduct: int | None = Field(default=None, ge=1, le=5)
    feedback_text: str | None = None


def _profile_dict(p: Any) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "business_name": p.business_name,
        "verification_status": p.verification_status,
        "account_status": p.account_status,
        "service_category_slugs": p.service_category_slugs,
    }


@router.get("/settings")
def get_settings_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_READ)
    return service.settings_dict(_settings(session, ctx.organisation_id))


@router.patch("/settings")
def patch_settings_api(
    body: SettingsBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.update_settings(session, ctx, body.model_dump(exclude_unset=True))
    return service.settings_dict(row)


@router.get("/categories")
def list_categories_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> list[dict[str, Any]]:
    return service.list_categories(session, ctx)


@router.post("/register")
def register_api(
    body: RegistrationBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    profile = service.submit_registration(session, ctx, body.model_dump())
    return _profile_dict(profile)


@router.post("/profiles/{profile_id}/verify")
def verify_api(
    profile_id: uuid.UUID,
    body: VerificationBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    profile = service.review_contractor(session, ctx, profile_id, decision=body.decision, notes=body.notes)
    return _profile_dict(profile)


@router.get("/marketplace")
def marketplace_search_api(
    category: str | None = Query(default=None),
    location: str | None = Query(default=None),
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> list[dict[str, Any]]:
    service.assert_addon(session, service.get_settings(), ctx.organisation_id)
    return service.search_marketplace(session, ctx, category=category, location=location)


@router.post("/jobs")
def create_job_api(
    body: JobBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    job = service.create_job(session, ctx, body.model_dump())
    return {"id": str(job.id), "reference_number": job.reference_number, "status": job.status}


@router.post("/quotations")
def submit_quotation_api(
    body: QuotationBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    quote = service.submit_quotation(session, ctx, body.model_dump())
    return {"id": str(quote.id), "quotation_reference": quote.quotation_reference, "status": quote.status}


@router.post("/quotations/{quotation_id}/approve")
def approve_quotation_api(
    quotation_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    quote = service.approve_quotation(session, ctx, quotation_id)
    return {"id": str(quote.id), "status": quote.status}


@router.post("/jobs/{job_id}/assign/{profile_id}")
def assign_job_api(
    job_id: uuid.UUID,
    profile_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    job = service.assign_job(session, ctx, job_id, profile_id)
    return {"id": str(job.id), "status": job.status, "assigned_contractor_profile_id": str(job.assigned_contractor_profile_id)}


@router.get("/workspace/jobs")
def workspace_jobs_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> list[dict[str, Any]]:
    service.assert_addon(session, service.get_settings(), ctx.organisation_id)
    return service.workspace_jobs(session, ctx)


@router.post("/workspace/jobs/{job_id}/complete")
def complete_job_api(
    job_id: uuid.UUID,
    body: CompletionBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    completion = service.submit_completion(session, ctx, job_id, body.model_dump())
    return {"id": str(completion.id), "review_status": completion.review_status}


@router.post("/completions/{completion_id}/review")
def review_completion_api(
    completion_id: uuid.UUID,
    body: CompletionReviewBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    completion = service.review_completion(session, ctx, completion_id, review_status=body.review_status, review_notes=body.review_notes)
    return {"id": str(completion.id), "review_status": completion.review_status}


@router.post("/feedback")
def feedback_api(
    body: FeedbackBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.submit_feedback(session, ctx, body.model_dump())
    return {"id": str(row.id), "moderation_status": row.moderation_status}


@router.get("/reports/dashboard")
def reports_dashboard_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> dict[str, Any]:
    return service.admin_dashboard(session, ctx)
