"""F3.6 document check results. Previous results are kept per document version."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentCheckRule(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "document_check_rules"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "category_code",
            "rule_kind",
            "parameter",
            name="uq_document_check_rules_org_cat_kind_param",
        ),
    )

    category_code: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    rule_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    parameter: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DocumentCheck(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "document_checks"
    __table_args__ = (
        Index("ix_document_checks_doc_version", "document_id", "document_version_id"),
        Index("ix_document_checks_org_status", "organisation_id", "status"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_document_versions.id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    checker_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="processing")
    extraction_status: Mapped[str] = mapped_column(String(32), nullable=False, default="failed")
    detected_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_needed")
    ai_error: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prompt_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    generation_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class DocumentCheckFinding(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "document_check_findings"
    __table_args__ = (Index("ix_document_check_findings_check", "check_id"),)

    check_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_checks.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    needs_human_verification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="rule")


class DocumentCheckObservation(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "document_check_observations"
    __table_args__ = (Index("ix_document_check_observations_check", "check_id"),)

    check_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_checks.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_finding_code: Mapped[str] = mapped_column(String(64), nullable=False)
    needs_human_verification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="structured_heuristic")
    created_at_override: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
