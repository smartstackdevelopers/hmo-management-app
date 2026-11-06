"""Pydantic schemas for F2.2 scheduling."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ShiftStatus = Literal["scheduled", "cancelled", "completed"]
VisitStatus = Literal["scheduled", "confirmed", "in_progress", "completed", "cancelled", "missed"]
TaskStatus = Literal["open", "in_progress", "blocked", "completed", "cancelled"]
TaskPriority = Literal["low", "normal", "high", "urgent"]


class ShiftCreate(BaseModel):
    staff_user_id: uuid.UUID
    shift_date: date
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(default="Europe/London", max_length=64)
    shift_type: str = Field(default="standard", max_length=64)
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_window(self) -> ShiftCreate:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class ShiftUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    shift_type: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=4000)


class ShiftCancel(BaseModel):
    cancel_reason: str = Field(min_length=1, max_length=2000)


class ShiftConflictCheck(BaseModel):
    staff_user_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    exclude_shift_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_window(self) -> ShiftConflictCheck:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class ShiftConflictResult(BaseModel):
    has_conflict: bool
    conflicting_shift_id: uuid.UUID | None = None


class ShiftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    staff_user_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    shift_date: date
    starts_at: datetime
    ends_at: datetime
    timezone: str
    shift_type: str
    location: str | None
    notes: str | None
    status: ShiftStatus
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime


class VisitCreate(BaseModel):
    tenant_id: uuid.UUID
    assigned_staff_user_id: uuid.UUID
    scheduled_at: datetime
    expected_duration_minutes: int | None = Field(default=None, ge=5, le=24 * 60)
    timezone: str = Field(default="Europe/London", max_length=64)
    visit_type: str = Field(default="support", max_length=64)
    purpose: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=10000)


class VisitUpdate(BaseModel):
    scheduled_at: datetime | None = None
    expected_duration_minutes: int | None = Field(default=None, ge=5, le=24 * 60)
    timezone: str | None = Field(default=None, max_length=64)
    visit_type: str | None = Field(default=None, max_length=64)
    purpose: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=10000)
    status: VisitStatus | None = None
    outcome: str | None = Field(default=None, max_length=10000)
    cancel_reason: str | None = Field(default=None, max_length=2000)
    linked_daily_log_id: uuid.UUID | None = None


class VisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    tenant_id: uuid.UUID
    assigned_staff_user_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    scheduled_at: datetime
    expected_duration_minutes: int | None
    timezone: str
    visit_type: str
    purpose: str
    location: str | None
    status: VisitStatus
    outcome: str | None
    notes: str | None
    cancel_reason: str | None
    completed_at: datetime | None
    linked_daily_log_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    assigned_user_id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    visit_id: uuid.UUID | None = None
    priority: TaskPriority = "normal"
    due_at: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    assigned_user_id: uuid.UUID | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    status: TaskStatus | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    title: str
    description: str | None
    assigned_user_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    tenant_id: uuid.UUID | None
    visit_id: uuid.UUID | None
    priority: TaskPriority
    due_at: datetime | None
    status: TaskStatus
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    overdue: bool = False


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    reminder_kind: str
    recipient_user_id: uuid.UUID
    scheduled_for: datetime
    status: str
    channel: str
    attempt_count: int
    last_attempt_at: datetime | None
    last_error: str | None
    payload_summary: str | None
    delivered: bool
    created_at: datetime
    updated_at: datetime
