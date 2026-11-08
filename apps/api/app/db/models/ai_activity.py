"""F3.14 AI activity transparency logs and wrong-answer feedback."""

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


class AiActivityLog(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Traceable AI operation record — no sensitive prompts or raw outputs."""

    __tablename__ = "ai_activity_logs"
    __table_args__ = (
        UniqueConstraint("request_id", name="uq_ai_activity_logs_request_id"),
        Index("ix_ai_activity_org_created", "organisation_id", "created_at"),
        Index("ix_ai_activity_org_feature", "organisation_id", "feature_id"),
        Index("ix_ai_activity_org_status", "organisation_id", "execution_status"),
        Index("ix_ai_activity_org_user", "organisation_id", "initiating_user_id"),
        Index("ix_ai_activity_org_visibility", "organisation_id", "visibility"),
    )

    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    usage_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_usage_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    initiating_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    feature_id: Mapped[str] = mapped_column(String(100), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(64), nullable=False, default="ai_operation")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    routing_info_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    cost_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_refs_json: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    sources_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    output_ref_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    human_approval_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_applicable"
    )
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Confidence: never fabricate percentages. Kind drives display.
    confidence_kind: Mapped[str] = mapped_column(String(64), nullable=False, default="unavailable")
    confidence_label: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Confidence unavailable"
    )
    confidence_detail_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    # staff = internal staff AI logs; initiator = only initiating user (+ reviewers)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="staff")
    metadata_safe_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")


class AiWrongAnswerFeedback(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "ai_wrong_answer_feedback"
    __table_args__ = (
        Index("ix_ai_feedback_org_status", "organisation_id", "review_status"),
        Index("ix_ai_feedback_org_activity", "organisation_id", "activity_id"),
        Index("ix_ai_feedback_org_created", "organisation_id", "created_at"),
        Index("ix_ai_feedback_org_category", "organisation_id", "category"),
    )

    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_activity_logs.id", ondelete="CASCADE"),
        nullable=False,
    )
    reporting_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")
    assigned_reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class AiFeedbackReviewEvent(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Immutable review history for wrong-answer feedback."""

    __tablename__ = "ai_feedback_review_events"
    __table_args__ = (
        Index("ix_ai_feedback_events_feedback", "feedback_id", "created_at"),
        Index("ix_ai_feedback_events_org", "organisation_id", "created_at"),
    )

    feedback_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_wrong_answer_feedback.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
