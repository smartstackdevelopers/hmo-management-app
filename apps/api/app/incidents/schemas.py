"""Pydantic schemas for F2.4 incidents, follow-ups, and workload."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IncidentStatus = Literal[
    "draft",
    "submitted",
    "under_review",
    "action_required",
    "resolved",
    "closed",
    "reopened",
]
IncidentSeverity = Literal["low", "normal", "high", "critical"]
FollowUpStatus = Literal["open", "in_progress", "blocked", "completed", "cancelled"]
FollowUpPriority = Literal["low", "normal", "high", "urgent"]


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(default="general", max_length=64)
    description: str = Field(min_length=1, max_length=20000)
    occurred_at: datetime
    tenant_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    room_id: uuid.UUID | None = None
    location: str | None = Field(default=None, max_length=255)
    severity: IncidentSeverity = "normal"
    immediate_actions: str | None = Field(default=None, max_length=10000)
    people_involved: str | None = Field(default=None, max_length=4000)
    witnesses: str | None = Field(default=None, max_length=4000)
    submit: bool = False


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, min_length=1, max_length=20000)
    occurred_at: datetime | None = None
    tenant_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    room_id: uuid.UUID | None = None
    location: str | None = Field(default=None, max_length=255)
    severity: IncidentSeverity | None = None
    immediate_actions: str | None = Field(default=None, max_length=10000)
    people_involved: str | None = Field(default=None, max_length=4000)
    witnesses: str | None = Field(default=None, max_length=4000)
    reviewer_user_id: uuid.UUID | None = None
    status: IncidentStatus | None = None
    resolution_notes: str | None = Field(default=None, max_length=10000)
    status_note: str | None = Field(default=None, max_length=500)


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    reference_number: str
    title: str
    category: str
    description: str
    occurred_at: datetime
    reported_by_user_id: uuid.UUID
    reviewer_user_id: uuid.UUID | None
    tenant_id: uuid.UUID | None
    property_id: uuid.UUID | None
    room_id: uuid.UUID | None
    location: str | None
    severity: IncidentSeverity
    immediate_actions: str | None
    people_involved: str | None
    witnesses: str | None
    status: IncidentStatus
    resolution_notes: str | None
    submitted_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    open_follow_up_count: int = 0


class IncidentHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    from_status: str | None
    to_status: str
    changed_by_user_id: uuid.UUID | None
    note: str | None
    created_at: datetime


class FollowUpCreate(BaseModel):
    description: str = Field(min_length=1, max_length=10000)
    assigned_user_id: uuid.UUID
    priority: FollowUpPriority = "normal"
    due_at: datetime | None = None


class FollowUpUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    assigned_user_id: uuid.UUID | None = None
    priority: FollowUpPriority | None = None
    due_at: datetime | None = None
    status: FollowUpStatus | None = None
    completion_notes: str | None = Field(default=None, max_length=10000)


class FollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    incident_id: uuid.UUID
    description: str
    assigned_user_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    priority: FollowUpPriority
    due_at: datetime | None
    status: FollowUpStatus
    completion_notes: str | None
    completed_by_user_id: uuid.UUID | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkloadStaffSummary(BaseModel):
    staff_user_id: uuid.UUID
    assigned_tenants: int
    open_tasks: int
    overdue_tasks: int
    upcoming_visits: int
    pending_handovers: int
    open_incident_follow_ups: int
    overdue_incident_follow_ups: int


class WorkloadResponse(BaseModel):
    organisation_id: uuid.UUID
    scope: Literal["own", "organisation"]
    staff: list[WorkloadStaffSummary]
