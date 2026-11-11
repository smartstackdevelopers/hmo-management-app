"""F5.5 wellbeing API contracts."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CheckinWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkin_date: date | None = None
    mood: str | None = Field(default=None, max_length=32)
    energy_level: int | None = Field(default=None, ge=1, le=5)
    stress_level: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = Field(default=None, max_length=2000)
    skipped: bool = False


class CheckinOut(BaseModel):
    id: uuid.UUID
    checkin_date: date
    mood: str | None
    energy_level: int | None
    stress_level: int | None
    notes: str | None
    skipped: bool
    created_at: datetime
    updated_at: datetime


class RoutineWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(default="other", max_length=64)
    start_time: time
    end_time: time | None = None
    recurrence: str = Field(default="daily", max_length=32)
    weekday_mask: int | None = Field(default=None, ge=0, le=127)
    one_time_date: date | None = None
    reminder_enabled: bool = False
    reminder_minutes_before: int | None = Field(default=None, ge=0, le=240)


class RoutineOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    category: str
    start_time: time
    end_time: time | None
    recurrence: str
    weekday_mask: int | None
    one_time_date: date | None
    is_active: bool
    reminder_enabled: bool
    reminder_minutes_before: int | None
    today_status: str | None = None


class RoutineStatusWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_date: date | None = None
    status: str = Field(pattern="^(completed|skipped)$")


class ResourceOut(BaseModel):
    id: uuid.UUID
    kind: str
    category: str
    title: str
    description: str | None
    instructions: str | None
    duration_minutes: int | None
    activity_level: str | None
    equipment: str | None
    safety_notes: str | None
    source_name: str | None
    source_url: str | None
    verification_status: str
    is_saved: bool = False


class ResourceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern="^(exercise|mindfulness)$")
    category: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    instructions: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=240)
    activity_level: str | None = Field(default=None, max_length=32)
    equipment: str | None = Field(default=None, max_length=255)
    safety_notes: str | None = None
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1000)
    verification_status: str = Field(default="unverified", max_length=32)
    is_active: bool = True


class ResourceCompletionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="completed", pattern="^(completed|stopped)$")


class DirectoryEntryOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    category: str
    address: str | None
    contact_info: str | None
    opening_hours: str | None
    eligibility: str | None
    referral_info: str | None
    source_url: str | None
    is_clinical: bool
    verification_status: str
    last_verified_at: datetime | None
    from_community_directory: bool = False


class DirectoryEntryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(min_length=1, max_length=64)
    address: str | None = Field(default=None, max_length=500)
    contact_info: str | None = Field(default=None, max_length=255)
    opening_hours: str | None = Field(default=None, max_length=255)
    eligibility: str | None = None
    referral_info: str | None = None
    source_url: str | None = Field(default=None, max_length=1000)
    community_service_id: uuid.UUID | None = None
    is_clinical: bool = False
    verification_status: str = Field(default="unverified", max_length=32)
    is_active: bool = True


class DashboardOut(BaseModel):
    disclaimer: str
    today_checkin: CheckinOut | None
    latest_mood: str | None
    today_routines: list[RoutineOut]
    routine_progress: dict[str, int]
    saved_exercise_count: int
    saved_mindfulness_count: int
    recent_checkins: list[CheckinOut]
    local_support_preview: list[DirectoryEntryOut]


class NavigatorCategoryOut(BaseModel):
    id: str
    title: str
    description: str


class NavigatorResultOut(BaseModel):
    disclaimer: str
    category: NavigatorCategoryOut
    directory_entries: list[DirectoryEntryOut]
    national_links: list[dict[str, Any]]
    crisis_guidance: str | None = None
