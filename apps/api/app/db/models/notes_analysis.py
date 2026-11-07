"""F3.4 Notes Analysis Agent — analysis records and human-reviewable suggestions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class DailyLogAiAnalysis(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "daily_log_ai_analyses"
    __table_args__ = (
        Index("ix_daily_log_ai_analyses_org_status", "organisation_id", "status"),
        Index("ix_daily_log_ai_analyses_log_version", "daily_log_id", "source_note_version"),
        UniqueConstraint(
            "daily_log_id",
            "source_note_version",
            "generation_kind",
            name="uq_daily_log_ai_analysis_log_version_kind",
        ),
    )

    daily_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_logs.id", ondelete="RESTRICT"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_note_version: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False, default="notes_analysis")
    feature_id: Mapped[str] = mapped_column(String(100), nullable=False, default="ai.agent.notes_analysis")
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    generation_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="on_demand")
    # on_demand | batch
    generation_method: Mapped[str] = mapped_column(String(32), nullable=False, default="llm")
    # llm | structured_heuristic
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review")
    # pending_review | approved | partially_approved | rejected | applied | failed
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_observations_json: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    missing_details_json: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    suggested_actions_json: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    uncertainty_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_refs_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DailyLogAiSuggestion(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "daily_log_ai_suggestions"
    __table_args__ = (
        Index("ix_daily_log_ai_suggestions_status", "organisation_id", "review_status"),
        Index("ix_daily_log_ai_suggestions_analysis", "analysis_id"),
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_log_ai_analyses.id", ondelete="CASCADE"), nullable=False
    )
    daily_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_logs.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    # missing_detail | next_action | observation
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_interpretation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    # pending | approved | rejected | dismissed | applied | superseded
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)
