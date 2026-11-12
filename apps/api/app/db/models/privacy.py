"""F7.2 privacy management models — technical records, not legal sign-off."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class PrivacyInventoryItem(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "privacy_inventory_items"
    __table_args__ = (
        UniqueConstraint("organisation_id", "category_code", name="uq_privacy_inventory_org_code"),
        Index("ix_privacy_inventory_org", "organisation_id"),
    )

    category_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_sources: Mapped[str | None] = mapped_column(Text, nullable=True)
    roles_with_access: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_locations: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_services: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_recipients: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_period_days: Mapped[int | None] = mapped_column(nullable=True)
    retention_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deletion_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    security_controls: Mapped[str | None] = mapped_column(Text, nullable=True)
    lawful_basis_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lawful_basis_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class PrivacyDpiaRegisterEntry(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "privacy_dpia_register"
    __table_args__ = (
        UniqueConstraint("organisation_id", "activity_key", name="uq_privacy_dpia_org_activity"),
        Index("ix_privacy_dpia_org_status", "organisation_id", "status"),
    )

    activity_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    personal_data_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    necessity_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    existing_safeguards: Mapped[str | None] = mapped_column(Text, nullable=True)
    additional_safeguards_required: Mapped[str | None] = mapped_column(Text, nullable=True)
    residual_risk_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    responsible_reviewer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    review_due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    approval_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approved_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PrivacyRetentionPolicy(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "privacy_retention_policies"
    __table_args__ = (
        UniqueConstraint("organisation_id", "category_code", name="uq_privacy_retention_org_code"),
        Index("ix_privacy_retention_org", "organisation_id", "status"),
    )

    category_code: Mapped[str] = mapped_column(String(64), nullable=False)
    category_label: Mapped[str] = mapped_column(String(200), nullable=False)
    retention_period_days: Mapped[int | None] = mapped_column(nullable=True)
    retention_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    review_due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    legal_hold_exception_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    authorised_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PrivacyDataSubjectRequest(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "privacy_data_subject_requests"
    __table_args__ = (
        Index("ix_privacy_dsr_org_status", "organisation_id", "status"),
        Index("ix_privacy_dsr_org_registered", "organisation_id", "registered_at"),
    )

    request_category: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="registered")
    subject_label: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    request_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_history: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)


class PrivacyRiskRegisterEntry(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "privacy_risk_register"
    __table_args__ = (Index("ix_privacy_risks_org_status", "organisation_id", "status"),)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    mitigation_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_review_at: Mapped[date | None] = mapped_column(Date, nullable=True)


class PrivacyDeletionLog(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Records authorised test-data purges — not production tenant records."""

    __tablename__ = "privacy_deletion_logs"
    __table_args__ = (Index("ix_privacy_deletion_logs_org", "organisation_id", "created_at"),)

    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    records_deleted: Mapped[int] = mapped_column(nullable=False, default=0)
    performed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class PrivacyTestRetentionRecord(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Synthetic rows for verifying retention purge workflows in non-production tests."""

    __tablename__ = "privacy_test_retention_records"
    __table_args__ = (Index("ix_privacy_test_retention_org_expires", "organisation_id", "expires_at"),)

    label: Mapped[str] = mapped_column(String(120), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
