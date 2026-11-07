"""F3.13 operational report drafts. Metrics are deterministic; narrative is AI-assisted draft only."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OperationalReportDraft(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "operational_report_drafts"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "period_type",
            "period_start",
            "period_end",
            "version",
            name="uq_operational_report_drafts_period_version",
        ),
        Index("ix_operational_report_drafts_org_period", "organisation_id", "period_start"),
        Index("ix_operational_report_drafts_org_status", "organisation_id", "status"),
    )

    period_type: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/London")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metrics_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    narrative_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_status: Mapped[str] = mapped_column(String(32), nullable=False, default="skipped")
    ai_notice: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="AI-GENERATED DRAFT — REQUIRES HUMAN REVIEW",
    )
    distributed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
