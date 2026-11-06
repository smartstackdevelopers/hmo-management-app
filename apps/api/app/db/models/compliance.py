"""F2.3 staff training records and safeguarding reminders."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
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
    from app.db.models.file_metadata import FileMetadata
    from app.db.models.organisation import Organisation
    from app.db.models.tenant import Tenant
    from app.db.models.user import User


class StaffTrainingRecord(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Staff training / certification record. Expiry intervals are organisation-defined."""

    __tablename__ = "staff_training_records"
    __table_args__ = (
        Index("ix_staff_training_staff_expiry", "staff_user_id", "expiry_date"),
        Index("ix_staff_training_org_status", "organisation_id", "status"),
        Index("ix_staff_training_org_category", "organisation_id", "category"),
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed', 'exempt')",
            name="ck_staff_training_status",
        ),
        CheckConstraint(
            "expiry_date IS NULL OR completion_date IS NULL OR expiry_date >= completion_date",
            name="ck_staff_training_expiry_after_completion",
        ),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    required_by_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    evidence_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    organisation: Mapped[Organisation] = relationship()
    staff: Mapped[User] = relationship(foreign_keys=[staff_user_id])
    evidence_file: Mapped[FileMetadata | None] = relationship()


class SafeguardingReminder(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Safeguarding follow-up reminder — not a case-management system.

    Titles/descriptions must stay non-sensitive; detailed case notes belong elsewhere.
    """

    __tablename__ = "safeguarding_reminders"
    __table_args__ = (
        Index("ix_safeguarding_reminders_assignee_due", "assigned_user_id", "due_at"),
        Index("ix_safeguarding_reminders_org_status", "organisation_id", "status"),
        CheckConstraint(
            "status IN ('pending', 'sent', 'acknowledged', 'completed', 'cancelled', 'overdue')",
            name="ck_safeguarding_reminders_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_safeguarding_reminders_priority",
        ),
    )

    related_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="follow_up")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped[Organisation] = relationship()
    assigned_user: Mapped[User] = relationship(foreign_keys=[assigned_user_id])
    tenant: Mapped[Tenant | None] = relationship()
