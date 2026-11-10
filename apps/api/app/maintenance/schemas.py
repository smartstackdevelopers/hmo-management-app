"""Pydantic schemas for F2.8 maintenance."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MaintPriority = Literal["low", "normal", "high", "urgent", "emergency"]
MaintStatus = Literal[
    "submitted",
    "acknowledged",
    "under_review",
    "awaiting_approval",
    "approved",
    "rejected",
    "assigned",
    "scheduled",
    "in_progress",
    "awaiting_parts",
    "on_hold",
    "completed",
    "closed",
    "reopened",
    "cancelled",
]
NoteVisibility = Literal["internal", "tenant_visible"]


class MaintenanceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=8000)
    category_code: str = Field(default="general", max_length=64)
    priority: MaintPriority = "normal"
    property_id: uuid.UUID
    room_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    requires_approval: bool = False


class MaintenanceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=8000)
    category_code: str | None = Field(default=None, max_length=64)
    if_match_updated_at: datetime | None = None


class AssignRequest(BaseModel):
    assigned_user_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=1000)


class PriorityRequest(BaseModel):
    priority: MaintPriority
    reason: str = Field(min_length=1, max_length=1000)


class StatusTransitionRequest(BaseModel):
    status: MaintStatus
    note: str | None = Field(default=None, max_length=1000)
    if_match_updated_at: datetime | None = None


class ScheduleVisitRequest(BaseModel):
    scheduled_at: datetime
    timezone: str = Field(default="Europe/London", max_length=64)
    assignee_user_id: uuid.UUID | None = None
    link_tenant_visit_id: uuid.UUID | None = None


class VisitRescheduleRequest(BaseModel):
    scheduled_at: datetime
    timezone: str = Field(default="Europe/London", max_length=64)
    assignee_user_id: uuid.UUID | None = None


class VisitCancelRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class VisitCompleteRequest(BaseModel):
    work_notes: str | None = Field(default=None, max_length=8000)
    missed: bool = False


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=2000)


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    visibility: NoteVisibility = "internal"
    if_match_updated_at: datetime | None = None


class CompleteRequest(BaseModel):
    work_notes: str = Field(min_length=1, max_length=8000)
    completion_summary: str | None = Field(default=None, max_length=8000)
    if_match_updated_at: datetime | None = None


class AssociatePhotoRequest(BaseModel):
    file_id: uuid.UUID
    caption: str | None = Field(default=None, max_length=500)
    photo_kind: Literal["problem", "completion"] = "problem"


class EmergencyContentUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=8000)
    approved_for_use: bool = False


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    description: str | None
    triggers_emergency_panel: bool
    emergency_kind: str | None


class CategoryCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    triggers_emergency_panel: bool = False
    emergency_kind: str | None = Field(default=None, max_length=32)
    sort_order: int = Field(default=100, ge=0, le=1_000_000)


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference_number: str
    title: str
    description: str
    category_code: str
    priority: str
    status: str
    property_id: uuid.UUID
    room_id: uuid.UUID | None
    tenant_id: uuid.UUID | None
    reported_by_user_id: uuid.UUID | None
    assigned_user_id: uuid.UUID | None
    requires_approval: bool
    approval_status: str | None
    scheduled_visit_at: datetime | None
    visit_timezone: str
    reported_at: datetime
    acknowledged_at: datetime | None
    completed_at: datetime | None
    closed_at: datetime | None
    work_notes: str | None
    completion_summary: str | None
    is_emergency_priority: bool
    show_emergency_panel: bool
    emergency_kind_hint: str | None = None
    file_ids: list[uuid.UUID] = []
    created_at: datetime
    updated_at: datetime


class VisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID
    assignee_user_id: uuid.UUID | None
    scheduled_at: datetime
    timezone: str
    status: str
    work_notes: str | None
    cancel_reason: str | None
    completed_at: datetime | None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visibility: str
    body: str
    created_at: datetime


class HistoryEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    summary: str
    detail: str | None
    created_at: datetime


class DashboardOut(BaseModel):
    total: int
    open_count: int
    by_priority: dict[str, int]
    emergency: int
    urgent_and_emergency: int
    awaiting_approval: int
    scheduled_visits: int
    in_progress: int
    overdue_scheduled: int
    recently_completed: int


class RequestFileOut(BaseModel):
    file_id: uuid.UUID
    caption: str | None
    photo_kind: str
    created_at: datetime


class EmergencyContentOut(BaseModel):
    kind: str
    title: str
    body: str
    requires_formal_approval: bool
    approved_for_use: bool
