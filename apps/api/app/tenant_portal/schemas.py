"""F4.1 tenant self-service contracts. Staff tenant schemas stay in records.schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import RecordStatus

COMMUNITY_CATEGORIES = frozenset({"food_bank", "kitchen", "clothing_bank", "local_service"})
DIRECTORY_PRIMARY_CATEGORIES = ("food_bank", "kitchen", "clothing_bank")
VERIFICATION_STATUSES = frozenset(
    {
        "pending_verification",
        "verified",
        "needs_review",
        "outdated",
        "inactive",
    }
)
CLOTHING_SERVICE_TYPES = frozenset({"provides_clothing", "accepts_donations", "both"})
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
    opening_days: str | None = None
    opening_hours: str | None = Field(default=None, max_length=255)
    eligibility: str | None = None
    referral_requirements: str | None = None
    contact: str | None = Field(default=None, max_length=255)
    service_instructions: str | None = None
    clothing_service_type: str | None = Field(default=None, max_length=32)
    information_source: str | None = Field(default=None, max_length=255)
    is_published: bool = False


class CommunityServiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    address_line: str | None = Field(default=None, max_length=255)
    opening_days: str | None = None
    opening_hours: str | None = Field(default=None, max_length=255)
    eligibility: str | None = None
    referral_requirements: str | None = None
    contact: str | None = Field(default=None, max_length=255)
    service_instructions: str | None = None
    clothing_service_type: str | None = Field(default=None, max_length=32)
    information_source: str | None = Field(default=None, max_length=255)
    is_published: bool | None = None


class CommunityServiceOut(BaseModel):
    """Tenant-facing directory record. Internal verification notes are never included."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    name: str
    description: str | None
    address_line: str | None
    opening_days: str | None = None
    opening_hours: str | None
    eligibility: str | None
    referral_requirements: str | None = None
    contact: str | None
    service_instructions: str | None = None
    clothing_service_type: str | None = None
    verification_status: str = "pending_verification"
    information_source: str | None = None
    verified_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_published: bool


class CommunityServiceAdminOut(CommunityServiceOut):
    """Admin view includes verification notes, actor ids, and geocode metadata."""

    verification_notes: str | None = None
    created_by_user_id: uuid.UUID | None = None
    updated_by_user_id: uuid.UUID | None = None
    verified_by_user_id: uuid.UUID | None = None
    latitude: float | None = None
    longitude: float | None = None
    geocode_status: str | None = None
    geocode_provider: str | None = None
    geocoded_at: datetime | None = None


class CommunityServiceVerifyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = None
    publish: bool = True


class CommunityServiceFlagBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = None


class CommunityServiceDeactivateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = None


class VerificationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    from_status: str | None
    to_status: str
    action: str
    notes: str | None
    actor_user_id: uuid.UUID | None
    created_at: datetime


class CommunityServicePage(BaseModel):
    items: list[CommunityServiceOut]
    page: int = 1
    page_size: int
    total: int

class CommunityServiceAdminPage(BaseModel):
    items: list[CommunityServiceAdminOut]
    page: int = 1
    page_size: int
    total: int


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
