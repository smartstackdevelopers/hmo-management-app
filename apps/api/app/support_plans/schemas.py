"""Pydantic schemas for F2.10 support plans."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PlanStatus = Literal["draft", "active", "under_review", "on_hold", "completed", "closed"]
GoalStatus = Literal["not_started", "in_progress", "at_risk", "achieved", "on_hold", "cancelled"]
GoalPriority = Literal["low", "normal", "high", "urgent"]
MilestoneStatus = Literal["pending", "in_progress", "completed", "delayed", "cancelled"]
ReviewType = Literal["weekly", "monthly"]
ReviewStatus = Literal["draft", "in_progress", "finalised", "superseded"]


class SupportPlanCreate(BaseModel):
    tenant_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    support_objectives: str | None = None
    responsible_worker_user_id: uuid.UUID
    start_date: date | None = None
    planned_review_date: date | None = None
    internal_notes: str | None = None
    tenant_summary: str | None = None
    contributor_user_ids: list[uuid.UUID] = Field(default_factory=list)


class SupportPlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    support_objectives: str | None = None
    responsible_worker_user_id: uuid.UUID | None = None
    start_date: date | None = None
    planned_review_date: date | None = None
    internal_notes: str | None = None
    tenant_summary: str | None = None
    contributor_user_ids: list[uuid.UUID] | None = None


class PlanTransitionBody(BaseModel):
    hold_reason: str | None = None


class SupportPlanReviseCreate(BaseModel):
    """Create a new draft plan superseding an existing one."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    support_objectives: str | None = None
    responsible_worker_user_id: uuid.UUID
    start_date: date | None = None
    planned_review_date: date | None = None
    internal_notes: str | None = None
    tenant_summary: str | None = None
    contributor_user_ids: list[uuid.UUID] = Field(default_factory=list)


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    intended_outcome: str | None = None
    responsible_user_id: uuid.UUID | None = None
    start_date: date | None = None
    target_date: date | None = None
    priority: GoalPriority = "normal"
    internal_notes: str | None = None


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    intended_outcome: str | None = None
    responsible_user_id: uuid.UUID | None = None
    start_date: date | None = None
    target_date: date | None = None
    priority: GoalPriority | None = None
    progress_notes: str | None = None
    internal_notes: str | None = None
    status: GoalStatus | None = None


class GoalProgressNoteCreate(BaseModel):
    body: str = Field(..., min_length=1)
    show_to_tenant: bool = False


class GoalAchieveBody(BaseModel):
    """Explicit achievement (sets status achieved)."""

    progress_notes: str | None = None


class GoalCancelBody(BaseModel):
    reason: str = Field(..., min_length=1)


class MilestoneCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    target_date: date | None = None
    responsible_user_id: uuid.UUID | None = None
    internal_notes: str | None = None


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    target_date: date | None = None
    responsible_user_id: uuid.UUID | None = None
    status: MilestoneStatus | None = None
    completion_notes: str | None = None
    internal_notes: str | None = None


class MilestoneCompleteBody(BaseModel):
    completion_notes: str | None = None


class MilestoneCancelBody(BaseModel):
    reason: str = Field(..., min_length=1)


class ReviewCreate(BaseModel):
    review_type: ReviewType
    review_date: date
    goals_reviewed: dict[str, Any] | None = None
    milestones_reviewed: dict[str, Any] | None = None
    progress_summary: str | None = None
    achievements: str | None = None
    challenges: str | None = None
    recommended_actions: str | None = None
    required_plan_changes: str | None = None
    follow_up_actions: str | None = None
    next_review_date: date | None = None
    internal_notes: str | None = None
    tenant_summary: str | None = None
    status: ReviewStatus = "draft"


class ReviewUpdate(BaseModel):
    review_date: date | None = None
    goals_reviewed: dict[str, Any] | None = None
    milestones_reviewed: dict[str, Any] | None = None
    progress_summary: str | None = None
    achievements: str | None = None
    challenges: str | None = None
    recommended_actions: str | None = None
    required_plan_changes: str | None = None
    follow_up_actions: str | None = None
    next_review_date: date | None = None
    internal_notes: str | None = None
    tenant_summary: str | None = None
    status: ReviewStatus | None = None


class ExportCreate(BaseModel):
    include_internal: bool = False


# --- Out views (plain dicts returned from service for flexibility) ---


class SupportPlanPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    reference_number: str
    tenant_id: uuid.UUID
    title: str
    description: str | None
    support_objectives: str | None
    responsible_worker_user_id: uuid.UUID
    start_date: date | None
    planned_review_date: date | None
    status: str
    completed_at: datetime | None
    closed_at: datetime | None
    hold_reason: str | None
    superseded_by_plan_id: uuid.UUID | None
    supersedes_plan_id: uuid.UUID | None
    version_number: int
    internal_notes: str | None = None
    tenant_summary: str | None = None
    created_by_user_id: uuid.UUID | None
    updated_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
