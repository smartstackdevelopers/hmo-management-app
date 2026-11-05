from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SurveyStatus = Literal["draft", "in_progress", "completed", "superseded"]
FeasibilityStatus = Literal[
    "suitable",
    "suitable_with_actions",
    "not_suitable",
    "further_assessment_required",
]
FindingSeverity = Literal["low", "medium", "high", "critical"]
FindingStatus = Literal["open", "in_progress", "resolved", "accepted_risk", "cancelled"]


class SurveyCreate(BaseModel):
    property_id: uuid.UUID
    survey_date: date | None = None
    surveyor_display_name: str | None = Field(default=None, max_length=255)
    site_contact_notes: str | None = Field(default=None, max_length=4000)


class SurveyUpdate(BaseModel):
    survey_date: date | None = None
    surveyor_display_name: str | None = Field(default=None, max_length=255)
    site_contact_notes: str | None = Field(default=None, max_length=4000)
    status: SurveyStatus | None = None
    building_assessment: dict[str, Any] | None = None
    facilities_assessment: dict[str, Any] | None = None
    health_safety_assessment: dict[str, Any] | None = None
    accessibility_assessment: dict[str, Any] | None = None
    camera_feasibility_notes: dict[str, Any] | None = None
    feasibility_status: FeasibilityStatus | None = None
    feasibility_summary: str | None = Field(default=None, max_length=8000)
    missing_information: str | None = Field(default=None, max_length=8000)
    recommendations: str | None = Field(default=None, max_length=8000)


class RoomAssessmentIn(BaseModel):
    room_id: uuid.UUID | None = None
    room_label: str = Field(min_length=1, max_length=100)
    assessment: dict[str, Any] = Field(default_factory=dict)


class FindingCreate(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    severity: FindingSeverity = "medium"
    description: str = Field(min_length=1, max_length=8000)
    recommended_action: str | None = Field(default=None, max_length=4000)
    related_room_id: uuid.UUID | None = None
    responsible_notes: str | None = Field(default=None, max_length=2000)
    target_date: date | None = None
    evidence_file_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)


class FindingUpdate(BaseModel):
    category: str | None = Field(default=None, max_length=64)
    severity: FindingSeverity | None = None
    description: str | None = Field(default=None, max_length=8000)
    recommended_action: str | None = Field(default=None, max_length=4000)
    related_room_id: uuid.UUID | None = None
    responsible_notes: str | None = Field(default=None, max_length=2000)
    target_date: date | None = None
    status: FindingStatus | None = None
    evidence_file_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)


class SurveyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    property_id: uuid.UUID
    status: str
    survey_date: date | None
    surveyor_user_id: uuid.UUID | None
    surveyor_display_name: str | None
    site_contact_notes: str | None
    building_assessment: dict[str, Any] | None
    facilities_assessment: dict[str, Any] | None
    health_safety_assessment: dict[str, Any] | None
    accessibility_assessment: dict[str, Any] | None
    camera_feasibility_notes: dict[str, Any] | None
    feasibility_status: str | None
    feasibility_summary: str | None
    missing_information: str | None
    recommendations: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RoomAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    survey_id: uuid.UUID
    room_id: uuid.UUID | None
    room_label: str
    assessment: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    survey_id: uuid.UUID
    category: str
    severity: str
    description: str
    recommended_action: str | None
    related_room_id: uuid.UUID | None
    responsible_notes: str | None
    target_date: date | None
    status: str
    evidence_file_id: uuid.UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
