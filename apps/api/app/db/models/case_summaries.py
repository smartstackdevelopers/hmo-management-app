"""F3.5 case summary versions. Previous versions are retained."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CaseSummary(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "case_summaries"
    __table_args__ = (
        UniqueConstraint("organisation_id", "tenant_id", "version_number", name="uq_case_summaries_org_tenant_version"),
        Index("ix_case_summaries_org_tenant", "organisation_id", "tenant_id"),
        Index("ix_case_summaries_org_status", "organisation_id", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False, default="case_summary")
    feature_id: Mapped[str] = mapped_column(String(100), nullable=False, default="ai.workflow.case_summaries")
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    generation_method: Mapped[str] = mapped_column(String(32), nullable=False, default="structured_heuristic")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review")
    sections_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    missing_information_json: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    recorded_concerns_json: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    source_refs_json: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    covered_from: Mapped[str | None] = mapped_column(String(32), nullable=True)
    covered_to: Mapped[str | None] = mapped_column(String(32), nullable=True)
    uncertainty_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
