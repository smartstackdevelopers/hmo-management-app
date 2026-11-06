"""Pydantic schemas for F2.3 training and safeguarding reminders."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TrainingStoredStatus = Literal["not_started", "in_progress", "completed", "exempt"]
TrainingDisplayStatus = Literal[
    "not_started", "in_progress", "completed", "exempt", "expiring_soon", "expired"
]
SafeguardingStatus = Literal[
    "pending", "sent", "acknowledged", "completed", "cancelled", "overdue"
]
SafeguardingPriority = Literal["low", "normal", "high", "urgent"]


class TrainingCreate(BaseModel):
    staff_user_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(default="general", max_length=64)
    provider: str | None = Field(default=None, max_length=255)
    completion_date: date | None = None
    expiry_date: date | None = None
    required_by_date: date | None = None
    evidence_file_id: uuid.UUID | None = None
    status: TrainingStoredStatus = "not_started"
    notes: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def validate_dates(self) -> TrainingCreate:
        if (
            self.completion_date is not None
            and self.expiry_date is not None
            and self.expiry_date < self.completion_date
        ):
            raise ValueError("expiry_date must be on or after completion_date")
        if self.status == "completed" and self.completion_date is None:
            raise ValueError("completion_date is required when status is completed")
        if self.status == "exempt":
            return self
        return self


class TrainingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=64)
    provider: str | None = Field(default=None, max_length=255)
    completion_date: date | None = None
    expiry_date: date | None = None
    required_by_date: date | None = None
    evidence_file_id: uuid.UUID | None = None
    status: TrainingStoredStatus | None = None
    notes: str | None = Field(default=None, max_length=10000)


class TrainingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    staff_user_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    title: str
    category: str
    provider: str | None
    completion_date: date | None
    expiry_date: date | None
    required_by_date: date | None
    evidence_file_id: uuid.UUID | None
    status: TrainingStoredStatus
    effective_status: TrainingDisplayStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class SafeguardingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(default="follow_up", max_length=64)
    description: str | None = Field(default=None, max_length=4000)
    due_at: datetime
    priority: SafeguardingPriority = "normal"
    assigned_user_id: uuid.UUID
    related_staff_user_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None


class SafeguardingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=4000)
    due_at: datetime | None = None
    priority: SafeguardingPriority | None = None
    assigned_user_id: uuid.UUID | None = None
    related_staff_user_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    status: SafeguardingStatus | None = None


class SafeguardingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    related_staff_user_id: uuid.UUID | None
    tenant_id: uuid.UUID | None
    assigned_user_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    category: str
    title: str
    description: str | None
    due_at: datetime
    priority: SafeguardingPriority
    status: SafeguardingStatus
    acknowledged_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
