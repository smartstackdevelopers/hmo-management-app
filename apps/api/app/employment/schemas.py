"""F5.3 employment preparation API contracts."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SkillItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=64)
    level: str | None = Field(default=None, max_length=32)
    years_experience: float | None = Field(default=None, ge=0, le=60)
    how_gained: str | None = Field(default=None, max_length=255)
    description: str | None = None
    is_custom: bool = False
    is_verified_certificate: bool = False


class ExperienceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern="^(employment|volunteer|project)$")
    title: str = Field(min_length=1, max_length=255)
    organisation: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    start_date: str | None = Field(default=None, max_length=32)
    end_date: str | None = Field(default=None, max_length=32)
    description: str | None = None


class EducationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution: str = Field(min_length=1, max_length=255)
    qualification: str | None = Field(default=None, max_length=255)
    year: str | None = Field(default=None, max_length=32)
    details: str | None = None


class AssessmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[SkillItem] | None = None
    experiences: list[ExperienceItem] | None = None
    education: list[EducationItem] | None = None
    qualifications: list[dict[str, Any]] | None = None
    certificates: list[dict[str, Any]] | None = None
    languages: list[dict[str, Any]] | None = None
    career_interests: list[str] | None = None
    preferred_work_types: list[str] | None = None
    employment_goals: str | None = None
    mark_completed: bool | None = None


class AssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    skills: list[Any]
    experiences: list[Any]
    education: list[Any]
    qualifications: list[Any]
    certificates: list[Any]
    languages: list[Any]
    career_interests: list[Any]
    preferred_work_types: list[Any]
    employment_goals: str | None
    completion_percent: int
    summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CvContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    personal_profile: str | None = None
    contact: dict[str, Any] | None = None
    employment: list[dict[str, Any]] | None = None
    education: list[dict[str, Any]] | None = None
    qualifications: list[dict[str, Any]] | None = None
    skills: list[dict[str, Any]] | None = None
    certificates: list[dict[str, Any]] | None = None
    volunteer: list[dict[str, Any]] | None = None
    projects: list[dict[str, Any]] | None = None
    languages: list[dict[str, Any]] | None = None
    references: list[dict[str, Any]] | None = None


class CvCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    template_id: str = Field(default="simple_professional", max_length=64)
    content: CvContent | None = None
    section_order: list[str] | None = None
    seed_from_assessment: bool = True
    is_default: bool = False


class CvUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    template_id: str | None = Field(default=None, max_length=64)
    content: CvContent | None = None
    section_order: list[str] | None = None
    is_default: bool | None = None


class CvOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    template_id: str
    content: dict[str, Any]
    section_order: list[Any]
    version: int
    is_default: bool
    pdf_file_id: uuid.UUID | None
    completion: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CvAssistRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1, max_length=64)
    original_text: str = Field(min_length=1, max_length=5000)


class CvAssistResponse(BaseModel):
    field: str
    original_text: str
    suggested_text: str
    provider: str
    requires_approval: bool = True
    disclaimer: str


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employer_name: str = Field(min_length=1, max_length=255)
    job_title: str = Field(min_length=1, max_length=255)
    job_location: str | None = Field(default=None, max_length=255)
    application_date: date | None = None
    source: str | None = Field(default=None, max_length=255)
    linked_cv_id: uuid.UUID | None = None
    contact_info: str | None = Field(default=None, max_length=255)
    status: str = Field(default="interested", max_length=32)
    interview_at: datetime | None = None
    follow_up_at: datetime | None = None
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employer_name: str | None = Field(default=None, min_length=1, max_length=255)
    job_title: str | None = Field(default=None, min_length=1, max_length=255)
    job_location: str | None = Field(default=None, max_length=255)
    application_date: date | None = None
    source: str | None = Field(default=None, max_length=255)
    linked_cv_id: uuid.UUID | None = None
    contact_info: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=32)
    interview_at: datetime | None = None
    follow_up_at: datetime | None = None
    notes: str | None = None
    is_archived: bool | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    employer_name: str
    job_title: str
    job_location: str | None
    application_date: date | None
    source: str | None
    linked_cv_id: uuid.UUID | None
    contact_info: str | None
    status: str
    interview_at: datetime | None
    follow_up_at: datetime | None
    notes: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ApplicationDashboard(BaseModel):
    total: int
    preparing: int
    submitted: int
    interviews_scheduled: int
    offers: int
    rejected: int
    upcoming_interviews: list[ApplicationOut]
    follow_ups_due: list[ApplicationOut]


class CareerGoalWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    suggested_activities: list[str] | None = None
    status: str = Field(default="pending", max_length=32)
    progress_notes: str | None = None


class CareerGoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None
    suggested_activities: list[Any]
    status: str
    progress_notes: str | None
    created_at: datetime
    updated_at: datetime


class RoadmapOut(BaseModel):
    current_skills: list[Any]
    career_interests: list[Any]
    employment_goals: str | None
    skill_gaps: list[str]
    suggested_learning: list[str]
    goals: list[CareerGoalOut]


class InterviewNoteWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: uuid.UUID | None = None
    interview_at: datetime | None = None
    notes: str | None = None
    questions_to_ask: str | None = None
    checklist: list[dict[str, Any]] | None = None


class InterviewNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    application_id: uuid.UUID | None
    interview_at: datetime | None
    notes: str | None
    questions_to_ask: str | None
    checklist: list[Any]
    common_questions: list[str]
    created_at: datetime
    updated_at: datetime


class StaffEmploymentSummary(BaseModel):
    tenant_id: uuid.UUID
    assessment_status: str | None
    completion_percent: int | None
    cv_count: int
    application_count: int
    open_goals: int
    skill_names: list[str]
    staff_support_notes: str | None = None
    career_goals: list[str] = Field(default_factory=list)


class StaffSupportNotesWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str = Field(min_length=1, max_length=5000)
