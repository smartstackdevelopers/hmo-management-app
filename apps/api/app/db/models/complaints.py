"""F2.7 complaints workflow: priorities, deadlines, escalations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.file_metadata import FileMetadata
    from app.db.models.housing import HousingApplication
    from app.db.models.organisation import Organisation
    from app.db.models.property import Property
    from app.db.models.tenant import Tenant
    from app.db.models.user import User


class ComplaintCategory(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Organisation-configurable complaint categories (not statutory classifications)."""

    __tablename__ = "complaint_categories"
    __table_args__ = (
        UniqueConstraint("organisation_id", "code", name="uq_complaint_categories_org_code"),
        Index("ix_complaint_categories_org_active", "organisation_id", "is_active"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)


class ComplaintDeadlineRule(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Operational deadline defaults by priority. Not statutory response periods."""

    __tablename__ = "complaint_deadline_rules"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id", "priority", name="uq_complaint_deadline_rules_org_priority"
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_complaint_deadline_rules_priority",
        ),
    )

    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    acknowledge_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=48)
    response_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    auto_escalate_overdue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="Internal operational target — not a statutory deadline.",
    )


class Complaint(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "complaints"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_complaints_org_ref"),
        Index("ix_complaints_org_status", "organisation_id", "status"),
        Index("ix_complaints_org_priority", "organisation_id", "priority"),
        Index("ix_complaints_assignee", "assigned_user_id", "status"),
        Index("ix_complaints_due", "organisation_id", "response_due_at"),
        CheckConstraint(
            "status IN ('submitted', 'acknowledged', 'under_review', 'investigation', "
            "'awaiting_information', 'escalated', 'resolved', 'closed', 'reopened', 'withdrawn')",
            name="ck_complaints_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_complaints_priority",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_code: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )
    housing_application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("housing_applications.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledge_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    response_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_visible_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    organisation: Mapped[Organisation] = relationship()
    tenant: Mapped[Tenant | None] = relationship()
    property: Mapped[Property | None] = relationship()
    housing_application: Mapped[HousingApplication | None] = relationship()


class ComplaintStatusHistory(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "complaint_status_history"
    __table_args__ = (
        Index("ix_complaint_status_history_complaint", "complaint_id", "created_at"),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class ComplaintHistoryEvent(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Chronological complaint timeline (tenant-safe events filtered in service)."""

    __tablename__ = "complaint_history_events"
    __table_args__ = (
        Index("ix_complaint_history_events_complaint", "complaint_id", "created_at"),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_tenant_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ComplaintNote(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "complaint_notes"
    __table_args__ = (
        Index("ix_complaint_notes_complaint", "complaint_id", "created_at"),
        CheckConstraint(
            "visibility IN ('internal', 'tenant_visible')",
            name="ck_complaint_notes_visibility",
        ),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ComplaintDeadlineChange(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "complaint_deadline_changes"
    __table_args__ = (
        Index("ix_complaint_deadline_changes_complaint", "complaint_id", "created_at"),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_value: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    new_value: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ComplaintEscalation(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "complaint_escalations"
    __table_args__ = (
        UniqueConstraint(
            "complaint_id", "idempotency_key", name="uq_complaint_escalations_idempotency"
        ),
        Index("ix_complaint_escalations_complaint", "complaint_id", "status"),
        CheckConstraint(
            "status IN ('open', 'resolved', 'cancelled')",
            name="ck_complaint_escalations_status",
        ),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    escalated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recipient_role: Mapped[str] = mapped_column(String(64), nullable=False, default="organisation_admin")
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    previous_assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    escalated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ComplaintFile(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "complaint_files"
    __table_args__ = (
        UniqueConstraint("complaint_id", "file_id", name="uq_complaint_files_complaint_file"),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    associated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_tenant_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    file: Mapped[FileMetadata] = relationship()
