"""F2.1 support caseload, daily logs, and handovers."""

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
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.organisation import Organisation
    from app.db.models.tenant import Tenant
    from app.db.models.user import User


class CaseAssignment(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Links a support worker to a tenant person within an organisation."""

    __tablename__ = "case_assignments"
    __table_args__ = (
        Index("ix_case_assignments_worker_status", "support_worker_user_id", "status"),
        Index("ix_case_assignments_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('active', 'ended', 'suspended')",
            name="ck_case_assignments_status",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    support_worker_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assignment_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    organisation: Mapped[Organisation] = relationship()
    tenant: Mapped[Tenant] = relationship()
    support_worker: Mapped[User] = relationship(foreign_keys=[support_worker_user_id])


class DailyLog(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Structured daily support log for an assigned tenant."""

    __tablename__ = "daily_logs"
    __table_args__ = (
        Index("ix_daily_logs_tenant_log_date", "tenant_id", "log_date"),
        Index("ix_daily_logs_author_log_date", "author_user_id", "log_date"),
        CheckConstraint(
            "status IN ('active', 'amended', 'voided')",
            name="ck_daily_logs_status",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activity_category: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    interaction_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    organisation: Mapped[Organisation] = relationship()
    tenant: Mapped[Tenant] = relationship()
    author: Mapped[User] = relationship(foreign_keys=[author_user_id])


class Handover(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Structured staff handover for continuity on a tenant case."""

    __tablename__ = "handovers"
    __table_args__ = (
        Index("ix_handovers_recipient_status", "recipient_user_id", "status"),
        Index("ix_handovers_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'acknowledged', 'completed', 'cancelled')",
            name="ck_handovers_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_handovers_priority",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    handover_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    case_updates: Mapped[str | None] = mapped_column(Text, nullable=True)
    outstanding_tasks: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped[Organisation] = relationship()
    tenant: Mapped[Tenant] = relationship()
