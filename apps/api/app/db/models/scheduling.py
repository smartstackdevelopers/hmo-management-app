"""F2.2 staff rota, tenant visits, operational tasks, and reminders."""

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.organisation import Organisation
    from app.db.models.tenant import Tenant
    from app.db.models.user import User


class StaffShift(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "staff_shifts"
    __table_args__ = (
        Index("ix_staff_shifts_staff_starts", "staff_user_id", "starts_at"),
        Index("ix_staff_shifts_org_date", "organisation_id", "shift_date"),
        CheckConstraint(
            "status IN ('scheduled', 'cancelled', 'completed')",
            name="ck_staff_shifts_status",
        ),
        CheckConstraint("ends_at > starts_at", name="ck_staff_shifts_ends_after_starts"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/London")
    shift_type: Mapped[str] = mapped_column(String(64), nullable=False, default="standard")
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    organisation: Mapped[Organisation] = relationship()
    staff: Mapped[User] = relationship(foreign_keys=[staff_user_id])


class TenantVisit(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_visits"
    __table_args__ = (
        Index("ix_tenant_visits_staff_scheduled", "assigned_staff_user_id", "scheduled_at"),
        Index("ix_tenant_visits_tenant_scheduled", "tenant_id", "scheduled_at"),
        CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'missed')",
            name="ck_tenant_visits_status",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_staff_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/London")
    visit_type: Mapped[str] = mapped_column(String(64), nullable=False, default="support")
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_daily_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_logs.id", ondelete="SET NULL"), nullable=True
    )

    organisation: Mapped[Organisation] = relationship()
    tenant: Mapped[Tenant] = relationship()


class OperationalTask(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "operational_tasks"
    __table_args__ = (
        Index("ix_operational_tasks_assignee_due", "assigned_user_id", "due_at"),
        Index("ix_operational_tasks_org_status", "organisation_id", "status"),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'blocked', 'completed', 'cancelled')",
            name="ck_operational_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_operational_tasks_priority",
        ),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_visits.id", ondelete="SET NULL"), nullable=True
    )
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped[Organisation] = relationship()


class ReminderRecord(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Scheduled reminder with idempotent delivery attempts (F2.2).

    Actual email/SMS/in-app delivery is deferred to F2.12; this records intent and outcomes.
    """

    __tablename__ = "reminder_records"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "resource_type",
            "resource_id",
            "reminder_kind",
            "scheduled_for",
            name="uq_reminder_idempotency",
        ),
        Index("ix_reminder_records_due", "status", "scheduled_for"),
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'cancelled', 'skipped')",
            name="ck_reminder_records_status",
        ),
    )

    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    reminder_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="in_app")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
