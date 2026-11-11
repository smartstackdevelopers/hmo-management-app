"""F5.4 job matching API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MatchingProfileOut(BaseModel):
    tenant_id: uuid.UUID
    skills: list[Any]
    experiences: list[Any]
    education: list[Any]
    qualifications: list[Any]
    certificates: list[Any]
    languages: list[Any]
    career_interests: list[Any]
    preferred_work_types: list[Any]
    employment_goals: str | None
    selected_cv_id: uuid.UUID | None
    cv_skills: list[Any]
    cv_title: str | None
    assessment_completion_percent: int
    note: str


class PreferencesOut(BaseModel):
    preferred_categories: list[str]
    preferred_locations: list[str]
    preferred_employment_types: list[str]
    preferred_experience_levels: list[str]
    career_interests: list[str]
    preferred_hours: str | None
    salary_min: int | None
    salary_max: int | None
    selected_cv_id: uuid.UUID | None


class PreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_categories: list[str] | None = None
    preferred_locations: list[str] | None = None
    preferred_employment_types: list[str] | None = None
    preferred_experience_levels: list[str] | None = None
    career_interests: list[str] | None = None
    preferred_hours: str | None = Field(default=None, max_length=64)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    selected_cv_id: uuid.UUID | None = None
    reset: bool | None = None


class JobListingOut(BaseModel):
    id: uuid.UUID
    title: str
    employer_name: str
    description: str | None
    location: str | None
    employment_type: str | None
    salary_text: str | None
    required_skills: list[Any]
    required_qualifications: list[Any]
    experience_requirements: str | None
    source_name: str
    source_url: str | None
    published_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    score: float | None = None
    matching_skills: list[str] | None = None
    missing_skills: list[str] | None = None
    reasons: list[str] | None = None
    disclaimer: str | None = None


class JobSearchResponse(BaseModel):
    items: list[JobListingOut]
    total: int
    page: int
    page_size: int
    sources_used: list[str]
    sources_unavailable: list[dict[str, Any]]
    ai_used: bool = False
    disclaimer: str


class StructuredJobImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    employer_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=64)
    salary_text: str | None = Field(default=None, max_length=255)
    required_skills: list[str] = Field(default_factory=list)
    required_qualifications: list[str] = Field(default_factory=list)
    experience_requirements: str | None = None
    source_url: str | None = Field(default=None, max_length=1000)
    published_at: datetime | None = None
    expires_at: datetime | None = None


class StructuredJobImportBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[StructuredJobImport] = Field(min_length=1, max_length=100)


class TrainingOut(BaseModel):
    id: uuid.UUID
    provider_name: str
    title: str
    description: str | None
    eligibility: str | None
    duration: str | None
    cost_text: str | None
    is_free_verified: bool
    source_name: str
    source_url: str | None
    related_skills: list[Any]
    verification_status: str
    reasons: list[str] | None = None


class StructuredTrainingImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(min_length=1, max_length=255)
    provider_name: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    eligibility: str | None = None
    duration: str | None = None
    cost_text: str | None = None
    is_free_verified: bool = False
    source_url: str | None = None
    related_skills: list[str] = Field(default_factory=list)
    verification_status: str = "unverified"


class MatchExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: uuid.UUID
    question: str | None = Field(default=None, max_length=1000)


class MatchExplainResponse(BaseModel):
    job_id: uuid.UUID
    explanation: str
    provider: str
    requires_review: bool = True
    disclaimer: str


class AddToTrackerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: uuid.UUID
    linked_cv_id: uuid.UUID | None = None
    status: str = Field(default="interested", max_length=32)
    notes: str | None = None


class StaffMatchProgress(BaseModel):
    tenant_id: uuid.UUID
    saved_jobs: int
    match_count: int
    top_scores: list[float]
    career_goals: list[str]
    preferred_categories: list[str]
