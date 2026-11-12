"""F6.1 request/response schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RentRecordWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property_id: uuid.UUID
    room_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    period_start: date
    period_end: date
    due_date: date | None = None
    status: str = "due"
    tenancy_reference: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class RentRecordStatusWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    recorded_paid_note: str | None = Field(default=None, max_length=2000)


class RentRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    property_name: str | None = None
    room_id: uuid.UUID | None
    tenant_id: uuid.UUID | None
    tenant_name: str | None = None
    amount: Decimal
    currency: str
    period_start: date
    period_end: date
    due_date: date | None
    status: str
    tenancy_reference: str | None
    notes: str | None
    recorded_paid_at: datetime | None
    recorded_paid_note: str | None
    created_at: datetime
    updated_at: datetime


class InspectionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property_id: uuid.UUID
    room_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    scheduled_date: date
    status: str = "scheduled"
    notes: str | None = None
    findings: str | None = None
    follow_up_actions: str | None = None
    assigned_to_user_id: uuid.UUID | None = None
    completed_date: date | None = None


class InspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    property_name: str | None = None
    room_id: uuid.UUID | None
    title: str
    scheduled_date: date
    completed_date: date | None
    status: str
    effective_status: str
    notes: str | None
    findings: str | None
    follow_up_actions: str | None
    assigned_to_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class PortfolioFilters(BaseModel):
    property_id: uuid.UUID | None = None
    building: str | None = None  # matches property name/city contains
    date_from: date | None = None
    date_to: date | None = None
    tenancy_status: str | None = None
    inspection_status: str | None = None
    repair_status: str | None = None
