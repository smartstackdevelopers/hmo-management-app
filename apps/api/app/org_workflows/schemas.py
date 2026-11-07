"""Pydantic schemas for F2.13 organisation workflows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ApprovalSourceType = Literal[
    "housing_application",
    "managed_document_access",
    "maintenance_request",
    "custom_form_submission",
    "complaint",
    "evidence_item",
]

InboxStatus = Literal[
    "pending",
    "under_review",
    "additional_information_required",
    "approved",
    "rejected",
    "cancelled",
    "expired",
]

DecisionAction = Literal["approve", "reject", "request_information"]


class InboxItemOut(BaseModel):
    reference: str
    source_type: str
    source_id: uuid.UUID
    title: str
    status: str
    priority: str | None = None
    requester_user_id: uuid.UUID | None = None
    reviewer_user_id: uuid.UUID | None = None
    submitted_at: datetime | None = None
    is_overdue: bool = False
    related_url_path: str | None = None


class ApprovalDecide(BaseModel):
    action: DecisionAction
    reason: str | None = Field(default=None, max_length=10000)
    maintenance_temporary_hours: int | None = Field(default=None, ge=1, le=24 * 90)
    housing_add_to_waiting_list: bool = False


class AssignReviewer(BaseModel):
    reviewer_user_id: uuid.UUID


class WorkflowStep(BaseModel):
    order: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=128)
    reviewer_roles: list[str] = Field(default_factory=list)


class WorkflowCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    process_type: str = Field(min_length=1, max_length=64)
    steps: list[WorkflowStep] = Field(default_factory=list)
    reviewer_roles: list[str] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    steps: list[WorkflowStep] | None = None
    reviewer_roles: list[str] | None = None
    change_notes: str | None = Field(default=None, max_length=2000)


class CustomFormCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    form_schema: dict[str, Any] = Field(validation_alias="schema_json")
    workflow_id: uuid.UUID | None = None

    model_config = {"populate_by_name": True}


class CustomFormUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    form_schema: dict[str, Any] | None = Field(default=None, validation_alias="schema_json")
    workflow_id: uuid.UUID | None = None

    model_config = {"populate_by_name": True}


class SubmissionCreate(BaseModel):
    form_id: uuid.UUID
    answers: dict[str, Any] = Field(default_factory=dict)
    tenant_id: uuid.UUID | None = None
    save_as_draft: bool = False


class SubmissionReview(BaseModel):
    action: DecisionAction
    reason: str | None = Field(default=None, max_length=10000)


class SharingGrantCreate(BaseModel):
    resource_type: str = Field(min_length=1, max_length=64)
    resource_id: uuid.UUID
    recipient_user_id: uuid.UUID | None = None
    recipient_organisation_id: uuid.UUID | None = None
    purpose: str = Field(min_length=1, max_length=4000)
    scope: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        return v


class SharingRevoke(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class SharingAccessBody(BaseModel):
    token: str = Field(min_length=16, max_length=256)
