"""F2.8 maintenance and repairs management."""

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
    from app.db.models.organisation import Organisation
    from app.db.models.property import Property
    from app.db.models.room import Room
    from app.db.models.tenant import Tenant
    from app.db.models.user import User


class MaintenanceCategory(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Organisation-configurable maintenance categories (operational, not statutory)."""

    __tablename__ = "maintenance_categories"
    __table_args__ = (
        UniqueConstraint("organisation_id", "code", name="uq_maintenance_categories_org_code"),
        Index("ix_maintenance_categories_org_active", "organisation_id", "is_active"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggers_emergency_panel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    emergency_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)  # gas | fire | null
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)


class MaintenanceEmergencyContent(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Organisation gas/fire emergency guidance. Content must be formally approved before production."""

    __tablename__ = "maintenance_emergency_content"
    __table_args__ = (
        UniqueConstraint("organisation_id", "kind", name="uq_maintenance_emergency_org_kind"),
        CheckConstraint("kind IN ('gas', 'fire')", name="ck_maintenance_emergency_kind"),
    )

    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    requires_formal_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved_for_use: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class MaintenanceRequest(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_requests"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_maintenance_requests_org_ref"),
        Index("ix_maintenance_requests_org_status", "organisation_id", "status"),
        Index("ix_maintenance_requests_property", "property_id", "status"),
        Index("ix_maintenance_requests_assignee", "assigned_user_id", "status"),
        Index("ix_maintenance_requests_scheduled", "organisation_id", "scheduled_visit_at"),
        CheckConstraint(
            "status IN ('submitted', 'acknowledged', 'under_review', 'awaiting_approval', 'approved', "
            "'rejected', 'assigned', 'scheduled', 'in_progress', 'awaiting_parts', 'on_hold', "
            "'completed', 'closed', 'reopened', 'cancelled')",
            name="ck_maintenance_requests_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent', 'emergency')",
            name="ck_maintenance_requests_priority",
        ),
        CheckConstraint(
            "approval_status IS NULL OR approval_status IN ('pending', 'approved', 'rejected')",
            name="ck_maintenance_requests_approval_status",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_code: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reported_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scheduled_visit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    visit_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/London")
    linked_tenant_visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_visits.id", ondelete="SET NULL"), nullable=True
    )
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    work_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    property: Mapped[Property] = relationship()
    room: Mapped[Room | None] = relationship()
    tenant: Mapped[Tenant | None] = relationship()


class MaintenanceStatusHistory(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_status_history"
    __table_args__ = (Index("ix_maintenance_status_history_req", "request_id", "created_at"),)

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class MaintenanceHistoryEvent(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_history_events"
    __table_args__ = (Index("ix_maintenance_history_events_req", "request_id", "created_at"),)

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_tenant_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MaintenanceNote(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_notes"
    __table_args__ = (
        Index("ix_maintenance_notes_request", "request_id", "created_at"),
        CheckConstraint("visibility IN ('internal', 'tenant_visible')", name="ck_maintenance_notes_visibility"),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    body: Mapped[str] = mapped_column(Text, nullable=False)


class MaintenanceApproval(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_approvals"
    __table_args__ = (
        Index("ix_maintenance_approvals_request", "request_id", "created_at"),
        CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_maintenance_approvals_decision",
        ),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    approver_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MaintenanceVisit(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Maintenance visit slots; may optionally link to F2.2 tenant_visits for casework alignment."""

    __tablename__ = "maintenance_visits"
    __table_args__ = (
        Index("ix_maintenance_visits_org_scheduled", "organisation_id", "scheduled_at"),
        Index("ix_maintenance_visits_request", "request_id", "scheduled_at"),
        CheckConstraint(
            "status IN ('scheduled', 'rescheduled', 'completed', 'missed', 'cancelled')",
            name="ck_maintenance_visits_status",
        ),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/London")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    work_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_tenant_visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_visits.id", ondelete="SET NULL"), nullable=True
    )


class MaintenanceRequestFile(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_request_files"
    __table_args__ = (
        UniqueConstraint("request_id", "file_id", name="uq_maintenance_request_files_req_file"),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="problem")
    associated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    file: Mapped[FileMetadata] = relationship()


class MaintenancePriorityChange(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_priority_changes"
    __table_args__ = (Index("ix_maintenance_priority_changes_req", "request_id", "created_at"),)

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_priority: Mapped[str] = mapped_column(String(16), nullable=False)
    to_priority: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
