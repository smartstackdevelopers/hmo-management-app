"""F6.2 scheduled reports, secure export artifacts, and early-warning alerts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ReportExport(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Authorised downloadable export artifact (streamed or scheduled)."""

    __tablename__ = "report_exports"
    __table_args__ = (
        Index("ix_report_exports_org_created", "organisation_id", "created_at"),
        CheckConstraint(
            "report_category IN ("
            "'occupancy', 'housing', 'complaints', 'caseload', 'plans', 'dashboard'"
            ")",
            name="ck_report_exports_category",
        ),
        CheckConstraint(
            "export_format IN ('csv', 'pdf', 'xlsx')",
            name="ck_report_exports_format",
        ),
        CheckConstraint(
            "status IN ('ready', 'expired', 'revoked')",
            name="ck_report_exports_status",
        ),
    )

    report_category: Mapped[str] = mapped_column(String(32), nullable=False)
    export_format: Mapped[str] = mapped_column(String(8), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_metadata_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_metadata.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Users allowed to download; empty means creator + schedule manage / org admins via permission.
    allowed_user_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)


class ScheduledReport(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "scheduled_reports"
    __table_args__ = (
        Index("ix_scheduled_reports_org_enabled", "organisation_id", "is_enabled"),
        CheckConstraint(
            "report_category IN ("
            "'occupancy', 'housing', 'complaints', 'caseload', 'plans', 'dashboard'"
            ")",
            name="ck_scheduled_reports_category",
        ),
        CheckConstraint(
            "frequency IN ('daily', 'weekly', 'monthly')",
            name="ck_scheduled_reports_frequency",
        ),
        CheckConstraint(
            "export_format IN ('csv', 'pdf', 'xlsx')",
            name="ck_scheduled_reports_format",
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    report_category: Mapped[str] = mapped_column(String(32), nullable=False)
    export_format: Mapped[str] = mapped_column(String(8), nullable=False, default="csv")
    frequency: Mapped[str] = mapped_column(String(16), nullable=False)
    # Relative reporting window in days ending at run time (e.g. 7, 30).
    period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # List of user UUID strings authorised in the same organisation.
    recipient_user_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ScheduledReportRun(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "scheduled_report_runs"
    __table_args__ = (
        Index("ix_scheduled_report_runs_schedule", "scheduled_report_id", "created_at"),
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')",
            name="ck_scheduled_report_runs_status",
        ),
    )

    scheduled_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scheduled_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    report_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_exports.id", ondelete="SET NULL"),
        nullable=True,
    )
    period_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EarlyWarningThreshold(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "early_warning_thresholds"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "alert_type",
            name="uq_early_warning_thresholds_org_type",
        ),
        CheckConstraint(
            "alert_type IN ("
            "'overdue_complaints', 'pending_housing', 'overdue_followups', "
            "'overdue_plan_reviews', 'occupancy_drop', 'high_caseload'"
            ")",
            name="ck_early_warning_thresholds_type",
        ),
    )

    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold_value: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class EarlyWarningAlert(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "early_warning_alerts"
    __table_args__ = (
        Index("ix_early_warning_alerts_org_status", "organisation_id", "status"),
        UniqueConstraint(
            "organisation_id",
            "dedupe_key",
            name="uq_early_warning_alerts_dedupe",
        ),
        CheckConstraint(
            "alert_type IN ("
            "'overdue_complaints', 'pending_housing', 'overdue_followups', "
            "'overdue_plan_reviews', 'occupancy_drop', 'high_caseload'"
            ")",
            name="ck_early_warning_alerts_type",
        ),
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved', 'dismissed')",
            name="ck_early_warning_alerts_status",
        ),
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="ck_early_warning_alerts_severity",
        ),
    )

    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="warning")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    threshold_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    related_refs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Prevents duplicate open alerts for the same condition window.
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
