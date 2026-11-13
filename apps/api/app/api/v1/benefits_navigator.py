"""F8.7 optional benefits navigator API."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.benefits_navigator import service
from app.benefits_navigator.service import _settings
from app.core.config import get_settings
from app.db.session import get_session
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/benefits-navigator", tags=["benefits-navigator"])


class SettingsBody(BaseModel):
    enabled: bool | None = None
    privacy_review_complete: bool | None = None
    ai_assistant_enabled: bool | None = None
    reminder_config: dict[str, Any] | None = None


class BenefitRecordBody(BaseModel):
    category_slug: str
    benefit_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    eligibility_information: str | None = None
    application_guidance: str | None = None
    required_evidence: list[str] | None = None
    official_source_id: uuid.UUID | None = None
    application_link: str | None = None
    geographic_coverage: str | None = None
    is_active: bool = False
    conditions: dict[str, Any] | None = None
    source_reference: str | None = None


class AssessmentBody(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    benefit_record_id: uuid.UUID | None = None
    tenant_user_id: uuid.UUID | None = None


class AiAskBody(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class ChecklistBody(BaseModel):
    items: list[dict[str, Any]]
    benefit_record_id: uuid.UUID | None = None


class ConsentBody(BaseModel):
    support_user_id: uuid.UUID


@router.get("/settings")
def get_settings_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_READ)
    return service.settings_dict(_settings(session, ctx.organisation_id))


@router.patch("/settings")
def patch_settings_api(
    body: SettingsBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.update_settings(session, ctx, body.model_dump(exclude_unset=True))
    return service.settings_dict(row)


@router.post("/directory")
def create_record_api(
    body: BenefitRecordBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.create_benefit_record(session, ctx, body.model_dump())
    return {"id": str(row.id), "benefit_name": row.benefit_name, "is_active": row.is_active}


@router.get("/search")
def search_api(
    category: str | None = Query(default=None),
    location: str | None = Query(default=None),
    housing: str | None = Query(default=None),
    employment: str | None = Query(default=None),
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> list[dict[str, Any]]:
    service.assert_addon(session, get_settings(), ctx.organisation_id)
    return service.search_benefits(session, ctx, category=category, location=location, housing=housing, employment=employment)


@router.post("/assessments")
def assess_api(
    body: AssessmentBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.run_assessment(session, ctx, body.model_dump())
    return {"id": str(row.id), "result_status": row.result_status, "explanation": row.result_explanation}


@router.post("/ai/ask")
def ai_ask_api(
    body: AiAskBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    return service.ask_ai(session, ctx, body.question)


@router.get("/tenant/dashboard")
def tenant_dashboard_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> dict[str, Any]:
    return service.tenant_dashboard(session, ctx)


@router.post("/saved/{benefit_id}")
def save_api(
    benefit_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.save_benefit(session, ctx, benefit_id)
    return {"id": str(row.id)}


@router.put("/checklist")
def checklist_api(
    body: ChecklistBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.upsert_checklist(session, ctx, body.items, body.benefit_record_id)
    return {"id": str(row.id), "items": row.items}


@router.post("/consent/staff")
def consent_api(
    body: ConsentBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.grant_staff_consent(session, ctx, body.support_user_id)
    return {"id": str(row.id), "support_user_id": str(row.support_user_id)}


@router.get("/community-support")
def community_api(
    location: str | None = Query(default=None),
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> list[dict[str, Any]]:
    return service.list_community_support(session, ctx, location)


@router.get("/reports/dashboard")
def reports_api(
    session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)
) -> dict[str, Any]:
    return service.admin_reports(session, ctx)
