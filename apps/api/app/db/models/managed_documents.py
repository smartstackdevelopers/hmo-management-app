"""F2.11 organisation document management: versions, expiry, retention, access, e-sign."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.file_metadata import FileMetadata
    from app.db.models.organisation import Organisation
    from app.db.models.user import User

# Note: ManagedDocument <-> ManagedDocumentVersion has two FK paths (document_id and
# current_version_id). Relationships must declare foreign_keys explicitly.


class ManagedDocumentCategory(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "managed_document_categories"
    __table_args__ = (
        UniqueConstraint("organisation_id", "code", name="uq_managed_doc_categories_org_code"),
        Index("ix_managed_doc_categories_org_active", "organisation_id", "is_active"),
        CheckConstraint(
            "access_classification IN ('standard', 'confidential', 'restricted')",
            name="ck_managed_doc_categories_classification",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_classification: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    organisation: Mapped["Organisation"] = relationship()


class OrganisationDocumentSettings(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Singleton per org: reminder windows (operational, not statutory)."""

    __tablename__ = "organisation_document_settings"
    __table_args__ = (UniqueConstraint("organisation_id", name="uq_org_document_settings_org"),)

    expiry_reminder_days_first: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    expiry_reminder_days_urgent: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    expiry_reminder_repeat_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=168)
    retention_default_review_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    organisation: Mapped["Organisation"] = relationship()


class ManagedDocument(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "managed_documents"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_managed_documents_org_ref"),
        Index("ix_managed_documents_org_status", "organisation_id", "status"),
        Index("ix_managed_documents_expiry", "organisation_id", "expiry_date"),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_managed_documents_status",
        ),
        CheckConstraint(
            "expiry_tracking IN ('none', 'valid', 'expiring_soon', 'expired', 'renewal_pending', 'renewed')",
            name="ck_managed_documents_expiry_tracking",
        ),
        CheckConstraint(
            "retention_status IN ('none', 'active', 'pending_review', 'archived', 'hold')",
            name="ck_managed_documents_retention_status",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_document_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("managed_document_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    access_classification: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_tracking: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    expiry_updated_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_expiry_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_policy_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retention_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    retention_review_due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    retention_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    archive_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    category: Mapped["ManagedDocumentCategory"] = relationship()
    organisation: Mapped["Organisation"] = relationship()
    versions: Mapped[list["ManagedDocumentVersion"]] = relationship(
        "ManagedDocumentVersion",
        back_populates="document",
        foreign_keys="ManagedDocumentVersion.document_id",
    )
    current_version: Mapped["ManagedDocumentVersion | None"] = relationship(
        "ManagedDocumentVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )
    links: Mapped[list["ManagedDocumentLink"]] = relationship(
        "ManagedDocumentLink",
        back_populates="document",
    )


class ManagedDocumentLink(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "managed_document_links"
    __table_args__ = (
        UniqueConstraint("document_id", "link_type", "link_id", name="uq_managed_doc_links_doc_type_id"),
        Index("ix_managed_doc_links_lookup", "organisation_id", "link_type", "link_id"),
        CheckConstraint(
            "link_type IN ('tenant', 'property', 'housing_application', 'support_plan', 'complaint', 'maintenance', 'other')",
            name="ck_managed_doc_links_type",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    link_type: Mapped[str] = mapped_column(String(32), nullable=False)
    link_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    document: Mapped["ManagedDocument"] = relationship(
        "ManagedDocument",
        back_populates="links",
    )


class ManagedDocumentVersion(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "managed_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_managed_doc_versions_doc_ver"),
        Index("ix_managed_doc_versions_document", "document_id", "version_number"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="RESTRICT"), nullable=False
    )
    change_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    document: Mapped["ManagedDocument"] = relationship(
        "ManagedDocument",
        back_populates="versions",
        foreign_keys=[document_id],
    )


class ManagedDocumentAccessRequest(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "managed_document_access_requests"
    __table_args__ = (
        Index("ix_managed_doc_access_req_doc", "document_id", "status"),
        CheckConstraint(
            "status IN ('submitted', 'under_review', 'approved', 'rejected', 'withdrawn', 'expired')",
            name="ck_managed_doc_access_req_status",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requester_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    temporary_access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ManagedDocumentAccessGrant(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "managed_document_access_grants"
    __table_args__ = (
        Index("ix_managed_doc_grants_user_exp", "user_id", "expires_at"),
        Index("ix_managed_doc_grants_doc", "document_id"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_document_access_requests.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ManagedDocumentSignatureRequest(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """In-platform signature record — not a qualified trust-service signature."""

    __tablename__ = "managed_document_signature_requests"
    __table_args__ = (
        Index("ix_managed_doc_sign_doc", "document_id", "status"),
        CheckConstraint(
            "status IN ('draft', 'pending_signature', 'signed', 'declined', 'cancelled', 'expired')",
            name="ck_managed_doc_sign_status",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_document_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    signer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    consent_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decline_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    document: Mapped["ManagedDocument"] = relationship()


class ManagedDocumentRetentionReview(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "managed_document_retention_reviews"
    __table_args__ = (Index("ix_managed_doc_ret_rev_doc", "document_id", "created_at"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_review_due_at: Mapped[date | None] = mapped_column(Date, nullable=True)


class ManagedDocumentReminderLog(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Idempotent expiry reminder dispatch (one row per document per run window)."""

    __tablename__ = "managed_document_reminder_logs"
    __table_args__ = (
        UniqueConstraint("document_id", "run_key", name="uq_managed_doc_reminder_doc_runkey"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_key: Mapped[str] = mapped_column(String(64), nullable=False)
    reminder_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
