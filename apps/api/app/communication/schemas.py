"""Pydantic schemas for F2.12 communication API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MAX_BODY_LEN = 50_000


class MessageSend(BaseModel):
    recipient_user_id: uuid.UUID
    subject: str | None = Field(default=None, max_length=500)
    body: str = Field(..., max_length=MAX_BODY_LEN)
    conversation_id: uuid.UUID | None = None
    conversation_tenant_id: uuid.UUID | None = None
    conversation_property_id: uuid.UUID | None = None
    conversation_maintenance_id: uuid.UUID | None = None
    related_resource_type: str | None = Field(default=None, max_length=64)
    related_resource_id: uuid.UUID | None = None


class MessageReadPatch(BaseModel):
    read: bool


class PreferenceUpdate(BaseModel):
    allow_in_app: bool | None = None
    allow_email: bool | None = None
    allow_sms: bool | None = None
    marketing_opt_out: bool | None = None
    sms_suppressed: bool | None = None


class OperationalSend(BaseModel):
    recipient_user_id: uuid.UUID
    channel: Literal["email", "sms"]
    subject: str | None = Field(default=None, max_length=500)
    body: str = Field(..., max_length=MAX_BODY_LEN)
    template_code: str | None = None
    template_variables: dict[str, str] = Field(default_factory=dict)
    essential_operational: bool = Field(
        default=True,
        description="When false, SMS/email respect marketing opt-out and SMS suppression.",
    )


class ReminderCreate(BaseModel):
    recipient_user_id: uuid.UUID
    reminder_kind: str = Field(..., max_length=64)
    channel: Literal["in_app", "email", "sms"]
    body: str = Field(..., max_length=MAX_BODY_LEN)
    subject: str | None = Field(default=None, max_length=500)
    scheduled_at: datetime
    resource_type: str | None = Field(default=None, max_length=64)
    resource_id: uuid.UUID | None = None

    @field_validator("scheduled_at")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("scheduled_at must be timezone-aware")
        return v


class AnnouncementCreate(BaseModel):
    title: str = Field(..., max_length=255)
    body: str = Field(..., max_length=MAX_BODY_LEN)
    priority: Literal["normal", "high", "emergency"] = "normal"
    audience: Literal["organisation_all", "staff_only", "tenants_only", "landlords_only", "custom_users"]
    channels: dict[str, bool]  # in_app, email, sms
    expires_at: datetime | None = None
    custom_user_ids: list[uuid.UUID] | None = None
    target_language: str | None = Field(default=None, max_length=16)
    require_translation_review: bool = False


class TranslationRequest(BaseModel):
    target_language: str = Field(..., min_length=2, max_length=16)
    target_field: Literal["title", "body"] = "body"
    source_language: str = Field(default="en", min_length=2, max_length=16)


class TranslationReview(BaseModel):
    translated_text: str = Field(..., max_length=MAX_BODY_LEN)


class TemplateCreate(BaseModel):
    code: str = Field(..., max_length=64, pattern=r"^[a-z][a-z0-9_]{1,62}$")
    title: str = Field(..., max_length=255)
    channel: Literal["in_app", "email", "sms"]
    subject_template: str | None = Field(default=None, max_length=500)
    body_template: str = Field(..., max_length=MAX_BODY_LEN)
    allowed_placeholders: list[str] = Field(default_factory=list)


class TemplateUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    subject_template: str | None = Field(default=None, max_length=500)
    body_template: str | None = Field(default=None, max_length=MAX_BODY_LEN)
    allowed_placeholders: list[str] | None = None
