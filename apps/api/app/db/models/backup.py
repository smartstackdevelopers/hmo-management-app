"""F7.3 backup run, schedule, and restore drill records."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class BackupScheduleConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Platform-wide backup schedule — not organisation-scoped."""

    __tablename__ = "backup_schedule_configs"
    __table_args__ = (UniqueConstraint("backup_type", "retention_tier", name="uq_backup_schedule_type_tier"),)

    backup_type: Mapped[str] = mapped_column(String(32), nullable=False)
    retention_tier: Mapped[str] = mapped_column(String(16), nullable=False, default="daily")
    cron_expression: Mapped[str] = mapped_column(String(64), nullable=False, default="0 3 * * *")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_parallel: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class BackupRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backup_runs"
    __table_args__ = (
        Index("ix_backup_runs_status_started", "status", "started_at"),
        Index("ix_backup_runs_type_started", "backup_type", "started_at"),
        UniqueConstraint("idempotency_key", name="uq_backup_runs_idempotency"),
    )

    backup_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="platform")
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, default="not_started")
    retention_tier: Mapped[str] = mapped_column(String(16), nullable=False, default="daily")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class RestoreDrillRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "restore_drill_runs"
    __table_args__ = (Index("ix_restore_drill_started", "started_at"),)

    environment_label: Mapped[str] = mapped_column(String(64), nullable=False, default="isolated-test")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    backup_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backup_runs.id"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    record_counts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rpo_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rto_seconds_measured: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpo_target_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_approval")
    rto_target_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_approval")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class BackupRetentionSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backup_retention_settings"

    retention_tier: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    keep_count: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
