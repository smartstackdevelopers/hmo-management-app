"""Pydantic schemas for F3.3 AI usage, budgets and dashboards."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BudgetUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_limit: Decimal = Field(..., ge=0, max_digits=12, decimal_places=4)
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    period_kind: Literal["calendar_month"] = "calendar_month"
    effective_from: date
    effective_to: date | None = None
    active: bool = True
    warning_threshold_pct: Decimal = Field(default=Decimal("80.00"), ge=0, le=100)
    default_reservation_amount: Decimal = Field(
        default=Decimal("0.0500"), ge=0, max_digits=12, decimal_places=4
    )
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("effective_to")
    @classmethod
    def _end_after_start(cls, value: date | None, info) -> date | None:  # type: ignore[no-untyped-def]
        start = info.data.get("effective_from")
        if value is not None and start is not None and value < start:
            raise ValueError("effective_to must be on or after effective_from")
        return value


class PricingUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(..., min_length=1, max_length=64)
    model_id: str = Field(..., min_length=1, max_length=128)
    pricing_version: str = Field(..., min_length=1, max_length=64)
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    input_price_per_1k_tokens: Decimal = Field(..., ge=0, max_digits=12, decimal_places=6)
    output_price_per_1k_tokens: Decimal = Field(..., ge=0, max_digits=12, decimal_places=6)
    effective_from: date
    effective_to: date | None = None
    active: bool = True
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, value: str) -> str:
        return value.strip().upper()


class ReserveBudgetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=8, max_length=64)
    organisation_id: UUID
    user_id: UUID | None = None
    feature_id: str = Field(..., min_length=1, max_length=100)
    workflow_id: str = Field(..., min_length=1, max_length=100)
    reserved_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    billable: bool = True
    cache_hit: bool = False


class ReconcileBudgetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=8, max_length=64)
    organisation_id: UUID
    execution_status: Literal["completed", "failed", "rejected_budget", "cancelled"]
    feature_id: str = Field(..., min_length=1, max_length=100)
    workflow_id: str = Field(..., min_length=1, max_length=100)
    user_id: UUID | None = None
    provider: str | None = None
    model_id: str | None = None
    prompt_id: str | None = None
    prompt_version: str | None = None
    provider_request_id: str | None = None
    batch_job_id: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cache_hit: bool | None = None
    escalation_occurred: bool | None = None
    escalation_reason: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_key: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    period_from: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    period_to: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    feature_id: str | None = None
    provider: str | None = None
    model_id: str | None = None
    execution_status: str | None = None
