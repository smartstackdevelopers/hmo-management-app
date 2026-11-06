"""F2.5 housing applications, waiting lists, and approval decisions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
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
    from app.db.models.organisation import Organisation
    from app.db.models.property import Property
    from app.db.models.tenant import Tenant
    from app.db.models.user import User


class HousingApplication(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "housing_applications"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id", "reference_number", name="uq_housing_applications_org_ref"
        ),
        Index("ix_housing_applications_org_status", "organisation_id", "status"),
        Index("ix_housing_applications_tenant", "tenant_id", "status"),
        Index("ix_housing_applications_reviewer", "reviewer_user_id", "status"),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'under_review', 'information_required', "
            "'approved', 'rejected', 'withdrawn', 'closed')",
            name="ck_housing_applications_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_housing_applications_priority",
        ),
    )

    reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    preferred_property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )
    accommodation_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    housing_requirements: Mapped[str] = mapped_column(Text, nullable=False)
    household_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    supporting_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    information_required_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped[Organisation] = relationship()
    tenant: Mapped[Tenant] = relationship()
    preferred_property: Mapped[Property | None] = relationship()


class HousingApplicationStatusHistory(
    UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base
):
    __tablename__ = "housing_application_status_history"
    __table_args__ = (
        Index("ix_housing_app_status_history_app", "application_id", "created_at"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("housing_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class HousingApplicationDecision(
    UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base
):
    __tablename__ = "housing_application_decisions"
    __table_args__ = (
        Index("ix_housing_app_decisions_app", "application_id", "created_at"),
        CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_housing_application_decisions_decision",
        ),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("housing_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    decided_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decision_notes: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WaitingListEntry(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Organisation waiting-list membership. Position is org-local, not a guarantee of allocation."""

    __tablename__ = "waiting_list_entries"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id", "application_id", name="uq_waiting_list_org_application"
        ),
        UniqueConstraint(
            "organisation_id", "position", name="uq_waiting_list_org_position"
        ),
        Index("ix_waiting_list_org_status", "organisation_id", "status"),
        CheckConstraint(
            "status IN ('active', 'paused', 'removed', 'allocated')",
            name="ck_waiting_list_entries_status",
        ),
        CheckConstraint("position > 0", name="ck_waiting_list_entries_position_positive"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("housing_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    responsible_officer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    application: Mapped[HousingApplication] = relationship()
