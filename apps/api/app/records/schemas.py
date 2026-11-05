from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models.enums import RecordStatus


class TenantCreate(BaseModel):
    preferred_name: str = Field(min_length=1, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    tenancy_reference: str | None = Field(default=None, max_length=100)
    consent_notes: str | None = None
    consent_given_at: datetime | None = None
    preferences: str | None = None
    needs_goals: str | None = None
    notes: str | None = None
    user_id: uuid.UUID | None = None


class TenantUpdate(BaseModel):
    preferred_name: str | None = Field(default=None, min_length=1, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    tenancy_reference: str | None = Field(default=None, max_length=100)
    consent_notes: str | None = None
    consent_given_at: datetime | None = None
    preferences: str | None = None
    needs_goals: str | None = None
    notes: str | None = None
    status: RecordStatus | None = None
    user_id: uuid.UUID | None = None


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    user_id: uuid.UUID | None
    preferred_name: str
    full_name: str | None
    email: str | None
    phone: str | None
    tenancy_reference: str | None
    consent_notes: str | None
    consent_given_at: datetime | None
    preferences: str | None
    needs_goals: str | None
    status: RecordStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PropertyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    postcode: str = Field(min_length=1, max_length=20)
    country_code: str = Field(default="GB", min_length=2, max_length=2)
    landlord_user_id: uuid.UUID | None = None
    notes: str | None = None


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address_line1: str | None = Field(default=None, min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    postcode: str | None = Field(default=None, min_length=1, max_length=20)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    landlord_user_id: uuid.UUID | None = None
    notes: str | None = None
    status: RecordStatus | None = None


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    name: str
    address_line1: str
    address_line2: str | None
    city: str
    region: str | None
    postcode: str
    country_code: str
    landlord_user_id: uuid.UUID | None
    status: RecordStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RoomCreate(BaseModel):
    property_id: uuid.UUID
    label: str = Field(min_length=1, max_length=100)
    floor_label: str | None = Field(default=None, max_length=50)
    room_type: str | None = Field(default=None, max_length=100)
    max_occupancy: int | None = Field(default=None, ge=1, le=100)
    notes: str | None = None

    @field_validator("max_occupancy")
    @classmethod
    def positive_capacity(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("max_occupancy must be a positive integer")
        return value


class RoomUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    floor_label: str | None = Field(default=None, max_length=50)
    room_type: str | None = Field(default=None, max_length=100)
    max_occupancy: int | None = Field(default=None, ge=1, le=100)
    notes: str | None = None
    status: RecordStatus | None = None


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    property_id: uuid.UUID
    label: str
    floor_label: str | None
    room_type: str | None
    max_occupancy: int | None
    status: RecordStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
