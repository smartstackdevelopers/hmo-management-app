"""Pydantic schemas for F2.6 evidence checklists and packs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EvidenceStatus = Literal[
    "pending",
    "received",
    "under_review",
    "accepted",
    "rejected",
    "missing",
    "not_applicable",
]


class ChecklistItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(default="general", max_length=64)
    description: str | None = Field(default=None, max_length=4000)
    is_required: bool = True
    sort_order: int = Field(default=100, ge=0, le=10000)


class ChecklistItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=4000)
    is_required: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=10000)
    status: EvidenceStatus | None = None
    reviewer_notes: str | None = Field(default=None, max_length=4000)
    rejection_reason: str | None = Field(default=None, max_length=4000)


class ChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    application_id: uuid.UUID
    category: str
    title: str
    description: str | None
    is_required: bool
    status: EvidenceStatus
    reviewer_notes: str | None
    rejection_reason: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by_user_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    sort_order: int
    created_at: datetime
    updated_at: datetime
    file_ids: list[uuid.UUID] = []


class AssociateFileRequest(BaseModel):
    file_id: uuid.UUID


class ReviewHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    checklist_item_id: uuid.UUID
    from_status: str | None
    to_status: str
    changed_by_user_id: uuid.UUID | None
    note: str | None
    created_at: datetime


class ReadinessOut(BaseModel):
    application_id: uuid.UUID
    ready: bool
    is_complete: bool
    required_total: int
    required_accepted: int
    outstanding: list[dict]


class GeneratePackRequest(BaseModel):
    allow_incomplete: bool = False


class EvidencePackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    application_id: uuid.UUID
    generated_by_user_id: uuid.UUID | None
    file_id: uuid.UUID | None
    status: str
    is_complete: bool
    outstanding_summary: str | None
    generated_at: datetime
    created_at: datetime


class TemplateCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(default="general", max_length=64)
    description: str | None = Field(default=None, max_length=4000)
    is_required: bool = True
    sort_order: int = Field(default=100, ge=0, le=10000)


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    code: str
    title: str
    category: str
    description: str | None
    is_required: bool
    sort_order: int
    is_active: bool
    created_at: datetime
