"""F3.9 compliance sweeps and findings. Rules decide gaps; AI only explains."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ComplianceSweep(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "compliance_sweeps"
    __table_args__ = (
        Index("ix_compliance_sweeps_org_started", "organisation_id", "started_at"),
        Index("ix_compliance_sweeps_org_status", "organisation_id", "status"),
    )

    trigger: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    scope_modules_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rules_evaluated_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    records_evaluated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_deduplicated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_needed")
    ai_error: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    feature_id: Mapped[str] = mapped_column(String(100), nullable=False, default="ai.agent.compliance")
    generation_method: Mapped[str] = mapped_column(String(32), nullable=False, default="rules_only")


class ComplianceFinding(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "compliance_findings"
    __table_args__ = (
        Index("ix_compliance_findings_org_status", "organisation_id", "review_status"),
        Index("ix_compliance_findings_sweep", "sweep_id"),
        Index("ix_compliance_findings_rule", "organisation_id", "rule_id"),
        Index("ix_compliance_findings_dedupe", "organisation_id", "dedupe_key"),
    )

    sweep_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_sweeps.id", ondelete="CASCADE"), nullable=False
    )
    first_sweep_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_sweeps.id", ondelete="CASCADE"), nullable=False
    )
    last_seen_sweep_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_sweeps.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_source: Mapped[str] = mapped_column(String(200), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    resolution_status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    needs_human_verification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrective_action_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
