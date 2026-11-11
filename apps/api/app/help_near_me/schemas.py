"""F5.2 Help Near Me request/response contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PostcodeValidateOut(BaseModel):
    postcode: str
    latitude: float
    longitude: float
    provider: str


class NearbyServiceOut(BaseModel):
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
    verification_status: str
    verified_at: datetime | None = None
    updated_at: datetime | None = None
    latitude: float
    longitude: float
    distance_km: float
    distance_miles: float


class NearbySearchOut(BaseModel):
    postcode: str
    latitude: float
    longitude: float
    radius_km: float
    sort: str
    page: int
    page_size: int
    total: int
    items: list[NearbyServiceOut]


class OutdatedReportWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=64)
    details: str | None = Field(default=None, max_length=2000)


class OutdatedReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    reason: str
    details: str | None
    status: str
    resolution_notes: str | None = None
    reviewed_by_user_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # Tenant responses omit reporter identity beyond own reports; admin includes it.
    reporter_user_id: uuid.UUID | None = None
    service_name: str | None = None
    service_category: str | None = None


class OutdatedReportAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1, max_length=32)
    resolution_notes: str | None = Field(default=None, max_length=2000)


class OutdatedReportPage(BaseModel):
    items: list[OutdatedReportOut]
    page: int
    page_size: int
    total: int


class ServiceGeocodeOut(BaseModel):
    id: uuid.UUID
    latitude: float | None
    longitude: float | None
    geocode_status: str
    geocode_provider: str | None
    geocoded_at: datetime | None


class ManualCoordinatesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
