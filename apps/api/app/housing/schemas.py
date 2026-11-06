"""Pydantic schemas for F2.5 housing applications."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApplicationStatus = Literal[
    "draft",
    "submitted",
    "under_review",
    "information_required",
    "approved",
    "rejected",
    "withdrawn",
    "closed",
]
ApplicationPriority = Literal["low", "normal", "high", "urgent"]
WaitingListStatus = Literal["active", "paused", "removed", "allocated"]
DecisionType = Literal["approved", "rejected"]


class ApplicationCreate(BaseModel):
    tenant_id: uuid.UUID
    housing_requirements: str = Field(min_length=1, max_length=10000)
    accommodation_type: str | None = Field(default=None, max_length=64)
    preferred_property_id: uuid.UUID | None = None
    household_summary: str | None = Field(default=None, max_length=4000)
    supporting_information: str | None = Field(default=None, max_length=10000)
    priority: ApplicationPriority = "normal"
    submit: bool = False


class ApplicationUpdate(BaseModel):
    housing_requirements: str | None = Field(default=None, min_length=1, max_length=10000)
    accommodation_type: str | None = Field(default=None, max_length=64)
    preferred_property_id: uuid.UUID | None = None
    household_summary: str | None = Field(default=None, max_length=4000)
    supporting_information: str | None = Field(default=None, max_length=10000)
    priority: ApplicationPriority | None = None
    reviewer_user_id: uuid.UUID | None = None
    information_required_notes: str | None = Field(default=None, max_length=4000)
    status: ApplicationStatus | None = None
    status_note: str | None = Field(default=None, max_length=1000)


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    reference_number: str
    tenant_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    reviewer_user_id: uuid.UUID | None
    preferred_property_id: uuid.UUID | None
    accommodation_type: str | None
    housing_requirements: str
    household_summary: str | None
    supporting_information: str | None
    priority: ApplicationPriority
    status: ApplicationStatus
    information_required_notes: str | None
    submitted_at: datetime | None
    decided_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    on_waiting_list: bool = False
    waiting_list_position: int | None = None


class ApplicationHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    from_status: str | None
    to_status: str
    changed_by_user_id: uuid.UUID | None
    note: str | None
    created_at: datetime


class DecisionCreate(BaseModel):
    decision: DecisionType
    decision_notes: str = Field(min_length=1, max_length=10000)
    add_to_waiting_list: bool = False


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    application_id: uuid.UUID
    decision: DecisionType
    decided_by_user_id: uuid.UUID
    decision_notes: str
    decided_at: datetime
    created_at: datetime


class InformationRequiredRequest(BaseModel):
    notes: str = Field(min_length=1, max_length=4000)


class WaitingListAdd(BaseModel):
    application_id: uuid.UUID
    priority: ApplicationPriority | None = None
    responsible_officer_user_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


class WaitingListUpdate(BaseModel):
    status: WaitingListStatus | None = None
    priority: ApplicationPriority | None = None
    responsible_officer_user_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


class WaitingListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    application_id: uuid.UUID
    position: int
    status: WaitingListStatus
    priority: ApplicationPriority
    responsible_officer_user_id: uuid.UUID | None
    added_at: datetime
    last_reviewed_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    application_reference: str | None = None
    application_status: str | None = None
    tenant_id: uuid.UUID | None = None
