"""F3.11 duplicate detection findings. Potential matches only — no auto merge/delete."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class DuplicateDetectionRun(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "duplicate_detection_runs"
    __table_args__ = (Index("ix_duplicate_detection_runs_org_started", "organisation_id", "started_at"),)

    trigger: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    scope_record_types_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    source_record_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidates_compared: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_deduplicated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    used_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DuplicateDetectionFinding(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "duplicate_detection_findings"
    __table_args__ = (
        Index("ix_duplicate_findings_org_status", "organisation_id", "review_status"),
        Index("ix_duplicate_findings_run", "run_id"),
        Index("ix_duplicate_findings_dedupe", "organisation_id", "dedupe_key"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("duplicate_detection_runs.id", ondelete="CASCADE"), nullable=False
    )
    first_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("duplicate_detection_runs.id", ondelete="CASCADE"), nullable=False
    )
    last_seen_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("duplicate_detection_runs.id", ondelete="CASCADE"), nullable=False
    )
    record_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    candidate_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(220), nullable=False)
    match_strength: Mapped[str] = mapped_column(String(32), nullable=False, default="possible")
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    matching_fields_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    matching_reasons_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
