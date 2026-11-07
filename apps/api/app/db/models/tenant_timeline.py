"""F2.9 tenant meetings, appointments, follow-ups, needs/goals."""

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


class TenantMeeting(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_meetings"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_tenant_meetings_org_ref"),
        Index("ix_tenant_meetings_tenant_scheduled", "tenant_id", "scheduled_at"),
        CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'completed', 'cancelled')",
            name="ck_tenant_meetings_status",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/London")
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meeting_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_visible_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    agreed_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped["Organisation"] = relationship()
    tenant: Mapped["Tenant"] = relationship()


class TenantMeetingParticipant(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_meeting_participants"
    __table_args__ = (
        UniqueConstraint("meeting_id", "user_id", name="uq_meeting_participants_meeting_user"),
        Index("ix_meeting_participants_user", "user_id"),
    )

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class TenantAppointment(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_appointments"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_tenant_appointments_org_ref"),
        Index("ix_tenant_appointments_tenant_start", "tenant_id", "starts_at"),
        CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'completed', 'cancelled', 'missed', 'rescheduled')",
            name="ck_tenant_appointments_status",
        ),
        CheckConstraint(
            "appointment_kind IN ('support', 'housing', 'administrative', 'property', 'other')",
            name="ck_tenant_appointments_kind",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    appointment_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="support")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/London")
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    attendance_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_tenant_visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_visits.id", ondelete="SET NULL"), nullable=True
    )

    organisation: Mapped["Organisation"] = relationship()
    tenant: Mapped["Tenant"] = relationship()


class TenantFollowUp(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_follow_ups"
    __table_args__ = (
        UniqueConstraint("organisation_id", "reference_number", name="uq_tenant_follow_ups_org_ref"),
        Index("ix_tenant_follow_ups_tenant_due", "tenant_id", "due_at"),
        Index("ix_tenant_follow_ups_assignee_due", "assigned_user_id", "due_at"),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'awaiting_information', 'completed', 'cancelled')",
            name="ck_tenant_follow_ups_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_tenant_follow_ups_priority",
        ),
        CheckConstraint(
            "related_type IN ('meeting', 'appointment', 'daily_log', 'handover', 'complaint', "
            "'maintenance', 'housing_application', 'incident', 'operational_task', 'tenant_visit', 'none')",
            name="ck_tenant_follow_ups_related_type",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_type: Mapped[str] = mapped_column(String(64), nullable=False, default="none")
    related_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    show_to_tenant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    organisation: Mapped["Organisation"] = relationship()
    tenant: Mapped["Tenant"] = relationship()


class TenantFollowUpChange(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Audit of assignee and due date changes."""

    __tablename__ = "tenant_follow_up_changes"
    __table_args__ = (Index("ix_follow_up_changes_follow_up", "follow_up_id", "created_at"),)

    follow_up_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_follow_ups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)


class TenantNeedGoal(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_needs_goals"
    __table_args__ = (
        Index("ix_tenant_needs_goals_tenant", "tenant_id", "created_at"),
        CheckConstraint(
            "record_kind IN ('need', 'goal')",
            name="ck_tenant_needs_goals_kind",
        ),
        CheckConstraint(
            "status IN ('identified', 'in_progress', 'achieved', 'paused', 'cancelled')",
            name="ck_tenant_needs_goals_status",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    category_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="identified")
    review_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organisation: Mapped["Organisation"] = relationship()
    tenant: Mapped["Tenant"] = relationship()
