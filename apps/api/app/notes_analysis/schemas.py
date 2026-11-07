"""Pydantic schemas for F3.4 Notes Analysis."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalyseNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    daily_log_id: UUID
    force: bool = False  # re-run even if an analysis exists for this version


class SuggestionDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject", "dismiss"]
    reviewer_note: str | None = Field(default=None, max_length=2000)
    edited_body: str | None = Field(default=None, max_length=4000)


class AnalysisReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "partially_approve", "reject"]
    review_comment: str | None = Field(default=None, max_length=2000)


class BatchEligibleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=200)
