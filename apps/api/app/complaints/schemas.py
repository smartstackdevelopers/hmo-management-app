"""Pydantic schemas for F2.7 complaints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ComplaintPriority = Literal["low", "normal", "high", "urgent"]
ComplaintStatus = Literal[
    "submitted",
    "acknowledged",
    "under_review",
    "investigation",
    "awaiting_information",
    "escalated",
    "resolved",
    "closed",
    "reopened",
    "withdrawn",
]
NoteVisibility = Literal["internal", "tenant_visible"]


class ComplaintCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=8000)
    category_code: str = Field(default="general", max_length=64)
    priority: ComplaintPriority = "normal"
    tenant_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    housing_application_id: uuid.UUID | None = None


class ComplaintUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=8000)
    category_code: str | None = Field(default=None, max_length=64)
    property_id: uuid.UUID | None = None
    housing_application_id: uuid.UUID | None = None
    tenant_visible_summary: str | None = Field(default=None, max_length=4000)


class AssignRequest(BaseModel):
    assigned_user_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=1000)


class PriorityRequest(BaseModel):
    priority: ComplaintPriority
    reason: str = Field(min_length=1, max_length=1000)


class StatusTransitionRequest(BaseModel):
    status: ComplaintStatus
    note: str | None = Field(default=None, max_length=1000)
    resolution_summary: str | None = Field(default=None, max_length=4000)
    tenant_visible_summary: str | None = Field(default=None, max_length=4000)


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    visibility: NoteVisibility = "internal"
    is_follow_up: bool = False


class DeadlineUpdateRequest(BaseModel):
    acknowledge_due_at: datetime | None = None
    response_due_at: datetime | None = None
    reason: str = Field(min_length=1, max_length=1000)


class EscalateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=4000)
    recipient_role: str = Field(default="organisation_admin", max_length=64)
    recipient_user_id: uuid.UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=128)


class ResolveEscalationRequest(BaseModel):
    outcome: str = Field(min_length=1, max_length=4000)


class AssociateFileRequest(BaseModel):
    file_id: uuid.UUID
    is_tenant_visible: bool = True


class CategoryCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=100, ge=0, le=10000)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    code: str
    title: str
    description: str | None
    is_active: bool
    sort_order: int


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    reference_number: str
    title: str
    description: str
    category_code: str
    priority: ComplaintPriority
    status: ComplaintStatus
    tenant_id: uuid.UUID | None
    submitted_by_user_id: uuid.UUID | None
    assigned_user_id: uuid.UUID | None
    property_id: uuid.UUID | None
    housing_application_id: uuid.UUID | None
    submitted_at: datetime
    acknowledged_at: datetime | None
    acknowledge_due_at: datetime | None
    response_due_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    resolution_summary: str | None = None
    tenant_visible_summary: str | None
    is_overdue: bool = False
    open_escalation: bool = False
    file_ids: list[uuid.UUID] = []
    created_at: datetime
    updated_at: datetime


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_id: uuid.UUID
    author_user_id: uuid.UUID | None
    visibility: NoteVisibility
    body: str
    is_follow_up: bool
    created_at: datetime


class HistoryEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_id: uuid.UUID
    event_type: str
    summary: str
    detail: str | None
    actor_user_id: uuid.UUID | None
    is_tenant_visible: bool
    created_at: datetime


class EscalationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_id: uuid.UUID
    idempotency_key: str
    reason: str
    escalated_by_user_id: uuid.UUID | None
    recipient_role: str
    recipient_user_id: uuid.UUID | None
    previous_assigned_user_id: uuid.UUID | None
    status: str
    outcome: str | None
    escalated_at: datetime
    resolved_at: datetime | None


class DashboardOut(BaseModel):
    total: int
    open_count: int
    by_priority: dict[str, int]
    awaiting_investigation: int
    upcoming_deadlines: int
    overdue: int
    escalated: int
    recently_resolved: int
