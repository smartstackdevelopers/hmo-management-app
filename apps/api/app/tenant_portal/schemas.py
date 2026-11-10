"""F4.1 tenant self-service contracts. Staff tenant schemas stay in records.schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import RecordStatus

COMMUNITY_CATEGORIES = frozenset({"food_bank", "kitchen", "clothing_bank", "local_service"})
OPPORTUNITY_KINDS = frozenset({"job", "training"})


class TenantSelfUpdate(BaseModel):
    """Tenants may change only these fields. Every other key is rejected."""

    model_config = ConfigDict(extra="forbid")

    preferred_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)


class TenantSelfOut(BaseModel):
    """Own profile. Notes, consent notes, and needs/goals are never included."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    user_id: uuid.UUID | None
    preferred_name: str
    full_name: str | None
    email: str | None
    phone: str | None
    tenancy_reference: str | None
    status: RecordStatus
    created_at: datetime
    updated_at: datetime


class HousingPropertyOut(BaseModel):
    id: uuid.UUID
    name: str
    address_line1: str
    address_line2: str | None
    city: str
    postcode: str


class HousingRoomOut(BaseModel):
    id: uuid.UUID
    label: str
    floor_label: str | None


class TenantHousingOut(BaseModel):
    tenancy_reference: str | None
    status: RecordStatus
    property: HousingPropertyOut | None
    room: HousingRoomOut | None


class CommunityServiceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    address_line: str | None = Field(default=None, max_length=255)
    opening_hours: str | None = Field(default=None, max_length=255)
    eligibility: str | None = None
    contact: str | None = Field(default=None, max_length=255)
    is_published: bool = False


class CommunityServiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    address_line: str | None = Field(default=None, max_length=255)
    opening_hours: str | None = Field(default=None, max_length=255)
    eligibility: str | None = None
    contact: str | None = Field(default=None, max_length=255)
    is_published: bool | None = None


class CommunityServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    name: str
    description: str | None
    address_line: str | None
    opening_hours: str | None
    eligibility: str | None
    contact: str | None
    is_published: bool


class OpportunityWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    eligibility: str | None = None
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=500)
    is_published: bool = False


class OpportunityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str | None = Field(default=None, min_length=1, max_length=32)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    eligibility: str | None = None
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=500)
    is_published: bool | None = None


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    title: str
    description: str | None
    eligibility: str | None
    source_name: str | None
    source_url: str | None
    is_published: bool
