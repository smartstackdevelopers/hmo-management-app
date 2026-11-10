"""Pydantic schemas for F2.1 support operations."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AssignmentStatus = Literal["active", "ended", "suspended"]
DailyLogStatus = Literal["active", "amended", "voided"]
HandoverStatus = Literal["draft", "submitted", "acknowledged", "completed", "cancelled"]
HandoverPriority = Literal["low", "normal", "high", "urgent"]

ACTIVITY_CATEGORIES = frozenset(
    {
        "welfare_check",
        "keywork",
        "housing",
        "health",
        "safeguarding",
        "appointment",
        "phone_call",
        "email",
        "other",
    }
)
INTERACTION_TYPES = frozenset(
    {
        "in_person",
        "phone",
        "video",
        "message",
        "collateral",
        "other",
    }
)


class CaseAssignmentCreate(BaseModel):
    tenant_id: uuid.UUID
    support_worker_user_id: uuid.UUID
    assignment_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("assignment_notes")
    @classmethod
    def strip_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class CaseAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    tenant_id: uuid.UUID
    support_worker_user_id: uuid.UUID
    assigned_by_user_id: uuid.UUID | None
    status: AssignmentStatus
    assigned_at: datetime
    ended_at: datetime | None
    assignment_notes: str | None
    created_at: datetime
    updated_at: datetime
    tenant_preferred_name: str | None = None
    tenant_full_name: str | None = None
    support_worker_display_name: str | None = None
    recent_log_count: int | None = None
    pending_handover_count: int | None = None


class DailyLogCreate(BaseModel):
    tenant_id: uuid.UUID
    log_date: date | None = None
    activity_category: str = Field(min_length=1, max_length=64)
    summary: str = Field(min_length=1, max_length=255)
    notes: str = Field(min_length=1, max_length=20000)
    interaction_type: str | None = Field(default=None, max_length=64)
    follow_up_required: bool = False
    next_action: str | None = Field(default=None, max_length=2000)

    @field_validator("activity_category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in ACTIVITY_CATEGORIES:
            raise ValueError(
                f"activity_category must be one of: {', '.join(sorted(ACTIVITY_CATEGORIES))}"
            )
        return cleaned

    @field_validator("interaction_type")
    @classmethod
    def validate_interaction(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if cleaned not in INTERACTION_TYPES:
            raise ValueError(
                f"interaction_type must be one of: {', '.join(sorted(INTERACTION_TYPES))}"
            )
        return cleaned

    @field_validator("summary", "notes")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("next_action")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class DailyLogUpdate(BaseModel):
    activity_category: str | None = Field(default=None, max_length=64)
    summary: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=20000)
    interaction_type: str | None = Field(default=None, max_length=64)
    follow_up_required: bool | None = None
    next_action: str | None = Field(default=None, max_length=2000)
    status: DailyLogStatus | None = None

    @field_validator("activity_category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if cleaned not in ACTIVITY_CATEGORIES:
            raise ValueError(
                f"activity_category must be one of: {', '.join(sorted(ACTIVITY_CATEGORIES))}"
            )
        return cleaned

    @field_validator("interaction_type")
    @classmethod
    def validate_interaction(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if cleaned not in INTERACTION_TYPES:
            raise ValueError(
                f"interaction_type must be one of: {', '.join(sorted(INTERACTION_TYPES))}"
            )
        return cleaned


class DailyLogRewriteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=20000)
    tenant_id: uuid.UUID | None = None

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class DailyLogRewriteOut(BaseModel):
    rewritten_text: str
    activity_id: uuid.UUID | None = None
    request_id: str | None = None
    prompt_version: str | None = None


class DailyLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    tenant_id: uuid.UUID
    author_user_id: uuid.UUID
    log_date: date
    logged_at: datetime
    activity_category: str
    summary: str
    notes: str
    interaction_type: str | None
    follow_up_required: bool
    next_action: str | None
    status: DailyLogStatus
    created_at: datetime
    updated_at: datetime


class HandoverCreate(BaseModel):
    tenant_id: uuid.UUID
    recipient_user_id: uuid.UUID
    summary: str = Field(min_length=1, max_length=255)
    case_updates: str | None = Field(default=None, max_length=20000)
    outstanding_tasks: str | None = Field(default=None, max_length=20000)
    follow_up_actions: str | None = Field(default=None, max_length=20000)
    priority: HandoverPriority = "normal"
    handover_at: datetime | None = None
    submit: bool = False

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class HandoverUpdate(BaseModel):
    summary: str | None = Field(default=None, max_length=255)
    case_updates: str | None = Field(default=None, max_length=20000)
    outstanding_tasks: str | None = Field(default=None, max_length=20000)
    follow_up_actions: str | None = Field(default=None, max_length=20000)
    priority: HandoverPriority | None = None


class HandoverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    tenant_id: uuid.UUID
    created_by_user_id: uuid.UUID
    recipient_user_id: uuid.UUID
    handover_at: datetime
    summary: str
    case_updates: str | None
    outstanding_tasks: str | None
    follow_up_actions: str | None
    priority: HandoverPriority
    status: HandoverStatus
    acknowledged_at: datetime | None
    acknowledged_by_user_id: uuid.UUID | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    tenant_preferred_name: str | None = None
