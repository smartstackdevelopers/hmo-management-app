"""Pydantic schemas for F2.9 tenant timeline APIs."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TimelineItemOut(BaseModel):
    """Aggregated pointer: deep link uses existing module APIs with same auth."""

    dedupe_key: str
    activity_type: str
    occurred_at: datetime
    sort_at: datetime
    title: str
    summary: str | None = None
    status: str | None = None
    responsible_user_id: uuid.UUID | None = None
    reference: str | None = None
    resource_type: str
    resource_id: uuid.UUID
    detail_api_path: str
    can_view: bool = True


class TimelinePageOut(BaseModel):
    items: list[TimelineItemOut]
    page: int
    page_size: int
    total: int


# --- Meetings ---


class MeetingParticipantIds(BaseModel):
    user_ids: list[uuid.UUID] = Field(default_factory=list)


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    purpose: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    scheduled_at: datetime
    duration_minutes: int | None = Field(None, ge=1, le=24 * 60)
    timezone: str = Field(default="Europe/London", max_length=64)
    location: str | None = Field(None, max_length=500)
    meeting_method: str | None = Field(None, max_length=64)
    responsible_user_id: uuid.UUID | None = None
    participants: MeetingParticipantIds | None = None
    tenant_visible_summary: str | None = None
    internal_notes: str | None = None
    status: Literal["scheduled", "confirmed"] = "scheduled"


class MeetingUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    purpose: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(None, ge=1, le=24 * 60)
    timezone: str | None = Field(None, max_length=64)
    location: str | None = Field(None, max_length=500)
    meeting_method: str | None = Field(None, max_length=64)
    responsible_user_id: uuid.UUID | None = None
    tenant_visible_summary: str | None = None
    internal_notes: str | None = None
    outcome: str | None = None
    agreed_actions: str | None = None
    participants: MeetingParticipantIds | None = None


class MeetingCompleteRequest(BaseModel):
    outcome: str | None = None
    agreed_actions: str | None = None
    completed_at: datetime | None = None


class MeetingCancelRequest(BaseModel):
    cancel_reason: str = Field(..., min_length=1)


class MeetingOut(BaseModel):
    id: uuid.UUID
    organisation_id: uuid.UUID
    tenant_id: uuid.UUID
    reference_number: str
    title: str
    purpose: str
    description: str | None
    scheduled_at: datetime
    duration_minutes: int | None
    timezone: str
    location: str | None
    meeting_method: str | None
    responsible_user_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    status: str
    tenant_visible_summary: str | None
    internal_notes: str | None = None
    outcome: str | None
    agreed_actions: str | None
    cancel_reason: str | None
    completed_at: datetime | None
    participant_user_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Appointments ---


class AppointmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    appointment_kind: Literal["support", "housing", "administrative", "property", "other"] = "support"
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    timezone: str = Field(default="Europe/London", max_length=64)
    location: str | None = Field(None, max_length=500)
    method: str | None = Field(None, max_length=64)
    assigned_user_id: uuid.UUID | None = None
    linked_tenant_visit_id: uuid.UUID | None = None
    status: Literal["scheduled", "confirmed"] = "scheduled"


class AppointmentUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    appointment_kind: Literal["support", "housing", "administrative", "property", "other"] | None = None
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = Field(None, max_length=64)
    location: str | None = Field(None, max_length=500)
    method: str | None = Field(None, max_length=64)
    assigned_user_id: uuid.UUID | None = None
    status: str | None = None
    attendance_status: str | None = None
    outcome: str | None = None
    cancel_reason: str | None = None
    linked_tenant_visit_id: uuid.UUID | None = None


class AppointmentCancelRequest(BaseModel):
    cancel_reason: str = Field(..., min_length=1)


class AppointmentOut(BaseModel):
    id: uuid.UUID
    organisation_id: uuid.UUID
    tenant_id: uuid.UUID
    reference_number: str
    appointment_kind: str
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime | None
    timezone: str
    location: str | None
    method: str | None
    assigned_user_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    status: str
    attendance_status: str | None
    outcome: str | None
    cancel_reason: str | None
    linked_tenant_visit_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Follow-ups (tenant_follow_ups) ---


class TenantFollowUpCreate(BaseModel):
    action_description: str = Field(..., min_length=1)
    instructions: str | None = None
    show_to_tenant: bool = False
    assigned_user_id: uuid.UUID
    due_at: datetime | None = None
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    internal_notes: str | None = None
    related_type: Literal[
        "meeting",
        "appointment",
        "daily_log",
        "handover",
        "complaint",
        "maintenance",
        "housing_application",
        "incident",
        "operational_task",
        "tenant_visit",
        "none",
    ] = "none"
    related_id: uuid.UUID | None = None


class TenantFollowUpUpdate(BaseModel):
    action_description: str | None = Field(None, min_length=1)
    instructions: str | None = None
    show_to_tenant: bool | None = None
    assigned_user_id: uuid.UUID | None = None
    due_at: datetime | None = None
    completed_at: datetime | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    status: (
        Literal[
            "open",
            "in_progress",
            "awaiting_information",
            "completed",
            "cancelled",
        ]
        | None
    ) = None
    internal_notes: str | None = None
    completion_notes: str | None = None
    cancel_reason: str | None = None


class TenantFollowUpCompleteRequest(BaseModel):
    completion_notes: str | None = None
    completed_at: datetime | None = None


class TenantFollowUpOut(BaseModel):
    id: uuid.UUID
    organisation_id: uuid.UUID
    tenant_id: uuid.UUID
    reference_number: str
    action_description: str
    instructions: str | None
    assigned_user_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    due_at: datetime | None
    priority: str
    status: str
    internal_notes: str | None = None
    completion_notes: str | None
    completed_at: datetime | None
    cancel_reason: str | None
    related_type: str
    related_id: uuid.UUID | None
    show_to_tenant: bool = False
    overdue: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Needs / Goals ---


class TenantNeedGoalCreate(BaseModel):
    record_kind: Literal["need", "goal"]
    category_code: str | None = Field(None, max_length=64)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    responsible_user_id: uuid.UUID | None = None
    status: Literal["identified", "in_progress", "achieved", "paused", "cancelled"] = "identified"
    review_at: date | None = None
    review_notes: str | None = None
    internal_notes: str | None = None


class TenantNeedGoalUpdate(BaseModel):
    category_code: str | None = Field(None, max_length=64)
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    responsible_user_id: uuid.UUID | None = None
    status: Literal["identified", "in_progress", "achieved", "paused", "cancelled"] | None = None
    review_at: date | None = None
    review_notes: str | None = None
    internal_notes: str | None = None


class TenantNeedGoalOut(BaseModel):
    id: uuid.UUID
    organisation_id: uuid.UUID
    tenant_id: uuid.UUID
    record_kind: str
    category_code: str | None
    title: str
    description: str
    responsible_user_id: uuid.UUID | None
    status: str
    review_at: date | None
    review_notes: str | None
    internal_notes: str | None = None
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
