"""Shared report filter validation (timezone-aware)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, field_validator

DateField = Literal["created_at", "submitted_at", "updated_at"]


class ReportDateRange(BaseModel):
    created_from: datetime | None = None
    created_to: datetime | None = None
    date_field: DateField = "created_at"

    @field_validator("created_from", "created_to")
    @classmethod
    def aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return v

    def validate_window(self) -> None:
        if self.created_from and self.created_to and self.created_from > self.created_to:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date range")


class HousingReportFilters(ReportDateRange):
    status: str | None = Field(default=None, max_length=32)
    reviewer_user_id: uuid.UUID | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class ComplaintsReportFilters(ReportDateRange):
    status: str | None = None
    priority: str | None = None
    overdue_only: bool = False
    escalated_only: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class CaseloadReportFilters(ReportDateRange):
    support_worker_user_id: uuid.UUID | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


def _now() -> datetime:
    return datetime.now(timezone.utc)
