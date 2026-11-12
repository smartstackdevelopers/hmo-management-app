"""F7.2 Privacy / GDPR management API."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.privacy import service as privacy_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/privacy", tags=["privacy"])


class InventoryUpdateBody(BaseModel):
    description: str | None = None
    purpose: str | None = None
    retention_period_days: int | None = None
    retention_notes: str | None = None
    lawful_basis_notes: str | None = None
    lawful_basis_confirmed: bool | None = None
    deletion_method: str | None = None
    security_controls: str | None = None


class DpiaUpdateBody(BaseModel):
    status: str | None = None
    purpose: str | None = None
    personal_data_summary: str | None = None
    necessity_notes: str | None = None
    risk_summary: str | None = None
    existing_safeguards: str | None = None
    additional_safeguards_required: str | None = None
    residual_risk_notes: str | None = None
    responsible_reviewer: str | None = None
    review_due_at: str | None = None
    approval_reference: str | None = None
    approved_by_name: str | None = None
    notes: str | None = None


class RetentionPolicyBody(BaseModel):
    category_code: str
    category_label: str | None = None
    retention_period_days: int | None = None
    retention_notes: str | None = None
    status: str = "draft"
    review_due_at: str | None = None
    legal_hold_exception_notes: str | None = None
    authorised_by_name: str | None = None


class DsrCreateBody(BaseModel):
    request_category: str = "access"
    subject_label: str = Field(min_length=1, max_length=200)
    subject_user_id: uuid.UUID | None = None
    request_summary: str | None = None
    assigned_user_id: uuid.UUID | None = None
    due_at: str | None = None


class DsrUpdateBody(BaseModel):
    status: str | None = None
    assigned_user_id: uuid.UUID | None = None
    completion_evidence: str | None = None
    response_note: str | None = None


class RiskCreateBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    severity: str = "medium"
    status: str = "open"
    mitigation_plan: str | None = None
    owner_label: str | None = None
    target_review_at: str | None = None


class TestRecordBody(BaseModel):
    label: str = "test-retention-row"
    expire_days: int = -1


@router.get("/dashboard")
def dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return privacy_service.dashboard(session, org)


@router.post("/bootstrap")
def bootstrap(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return privacy_service.bootstrap_catalog(session, org)


@router.get("/inventory")
def list_inventory(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return privacy_service.list_inventory(session, org)


@router.patch("/inventory/{item_id}")
def patch_inventory(
    item_id: uuid.UUID,
    body: InventoryUpdateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return privacy_service.update_inventory(session, org, item_id, body.model_dump(exclude_unset=True))


@router.get("/dpia")
def list_dpia(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return privacy_service.list_dpia(session, org)


@router.patch("/dpia/{entry_id}")
def patch_dpia(
    entry_id: uuid.UUID,
    body: DpiaUpdateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return privacy_service.update_dpia(session, org, entry_id, body.model_dump(exclude_unset=True))


@router.get("/retention")
def list_retention(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return privacy_service.list_retention_policies(session, org)


@router.put("/retention")
def put_retention(
    body: RetentionPolicyBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return privacy_service.upsert_retention_policy(session, org, body.model_dump())


@router.get("/data-subject-requests")
def list_dsr(
    status: str | None = Query(default=None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return privacy_service.list_dsr(session, org, status=status)


@router.post("/data-subject-requests")
def create_dsr(
    body: DsrCreateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return privacy_service.create_dsr(session, org, body.model_dump())


@router.patch("/data-subject-requests/{dsr_id}")
def patch_dsr(
    dsr_id: uuid.UUID,
    body: DsrUpdateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return privacy_service.update_dsr(session, org, dsr_id, body.model_dump(exclude_unset=True))


@router.get("/risks")
def list_risks(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return privacy_service.list_risks(session, org)


@router.post("/risks")
def create_risk(
    body: RiskCreateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return privacy_service.create_risk(session, org, body.model_dump())


@router.post("/retention/test-record")
def create_test_record(
    body: TestRecordBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return privacy_service.create_test_retention_record(session, org, body.label, body.expire_days)


@router.post("/retention/run-test-purge")
def run_test_purge(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return privacy_service.run_test_retention_purge(session, org)
