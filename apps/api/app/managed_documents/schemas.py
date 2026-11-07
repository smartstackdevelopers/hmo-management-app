"""Pydantic schemas for F2.11 managed documents."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

LinkType = Literal[
    "tenant",
    "property",
    "housing_application",
    "support_plan",
    "complaint",
    "maintenance",
    "other",
]
DocStatus = Literal["draft", "active", "archived"]
ExpiryTracking = Literal["none", "valid", "expiring_soon", "expired", "renewal_pending", "renewed"]
RetentionStatus = Literal["none", "active", "pending_review", "archived", "hold"]
AccessClass = Literal["standard", "confidential", "restricted"]
AccessReqStatus = Literal[
    "submitted", "under_review", "approved", "rejected", "withdrawn", "expired"
]
SignStatus = Literal[
    "draft", "pending_signature", "signed", "declined", "cancelled", "expired"
]


class CategoryCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    access_classification: AccessClass = "standard"
    sort_order: int = 100


class CategoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    access_classification: AccessClass | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class OrgDocSettingsUpdate(BaseModel):
    expiry_reminder_days_first: int | None = Field(default=None, ge=1, le=730)
    expiry_reminder_days_urgent: int | None = Field(default=None, ge=1, le=365)
    expiry_reminder_repeat_hours: int | None = Field(default=None, ge=1, le=24 * 60)
    retention_default_review_months: int | None = Field(default=None, ge=1, le=600)


class DocumentLinkIn(BaseModel):
    link_type: LinkType
    link_id: uuid.UUID
    label: str | None = Field(default=None, max_length=255)


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category_id: uuid.UUID
    access_classification: AccessClass = "standard"
    expiry_date: date | None = None
    retention_policy_label: str | None = Field(default=None, max_length=255)
    retention_start_date: date | None = None
    retention_review_due_at: date | None = None
    legal_hold: bool = False
    links: list[DocumentLinkIn] = Field(default_factory=list)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category_id: uuid.UUID | None = None
    access_classification: AccessClass | None = None
    links: list[DocumentLinkIn] | None = None


class ExpiryUpdate(BaseModel):
    expiry_date: date | None = None
    reason: str | None = None
    expiry_tracking: ExpiryTracking | None = None


class RetentionUpdate(BaseModel):
    retention_policy_label: str | None = None
    retention_start_date: date | None = None
    retention_review_due_at: date | None = None
    retention_status: RetentionStatus | None = None
    legal_hold: bool | None = None


class RetentionReviewCreate(BaseModel):
    notes: str | None = None
    next_review_due_at: date | None = None


class VersionCreateMeta(BaseModel):
    change_description: str | None = None


class AccessRequestCreate(BaseModel):
    reason: str = Field(..., min_length=1)


class AccessRequestDecide(BaseModel):
    approve: bool
    decision_reason: str | None = None
    temporary_hours: int | None = Field(default=72, ge=1, le=24 * 90)


class AccessGrantRevoke(BaseModel):
    reason: str | None = None


class SignatureRequestCreate(BaseModel):
    version_id: uuid.UUID
    signer_user_id: uuid.UUID
    consent_text: str | None = None
    expires_at: datetime | None = None


class SignatureDecline(BaseModel):
    reason: str | None = None


class SignatureConsent(BaseModel):
    """In-platform consent acknowledgement (not qualified e-sign)."""

    consent_text: str = Field(..., min_length=1)
    acknowledgement: str = Field(
        ...,
        description="Must match a fixed phrase to record intent",
        min_length=1,
    )


SIGN_ACK_PHRASE = "I acknowledge this in-platform record is not a qualified electronic signature."
