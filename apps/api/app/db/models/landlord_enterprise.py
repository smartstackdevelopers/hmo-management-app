"""F6.1 landlord enterprise: rent ledger and property inspections."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.property import Property
    from app.db.models.room import Room
    from app.db.models.tenant import Tenant
    from app.db.models.user import User


class RentRecord(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Rent ledger entry only — not a payment gateway transaction."""

    __tablename__ = "rent_records"
    __table_args__ = (
        Index("ix_rent_records_org_property_period", "organisation_id", "property_id", "period_start"),
        Index("ix_rent_records_org_status", "organisation_id", "status"),
        Index("ix_rent_records_tenant", "tenant_id", "period_start"),
        CheckConstraint(
            "status IN ('due', 'outstanding', 'recorded_paid', 'waived', 'cancelled')",
            name="ck_rent_records_status",
        ),
        CheckConstraint("period_end >= period_start", name="ck_rent_records_period"),
        CheckConstraint("amount >= 0", name="ck_rent_records_amount"),
        UniqueConstraint(
            "organisation_id",
            "property_id",
            "tenant_id",
            "period_start",
            "period_end",
            name="uq_rent_records_period_scope",
        ),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP", server_default="GBP")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="due", server_default="due")
    tenancy_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recorded_paid_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recorded_paid_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    housing_property: Mapped[Property] = relationship()
    room: Mapped[Room | None] = relationship()
    tenant: Mapped[Tenant | None] = relationship()
    recorded_paid_by: Mapped[User | None] = relationship(foreign_keys=[recorded_paid_by_user_id])


class PropertyInspection(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Landlord/property inspection record (separate from occupancy site surveys)."""

    __tablename__ = "property_inspections"
    __table_args__ = (
        Index("ix_property_inspections_org_property", "organisation_id", "property_id", "scheduled_date"),
        Index("ix_property_inspections_org_status", "organisation_id", "status"),
        CheckConstraint(
            "status IN ('scheduled', 'in_progress', 'completed', 'cancelled')",
            name="ck_property_inspections_status",
        ),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled", server_default="scheduled")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    housing_property: Mapped[Property] = relationship()
    room: Mapped[Room | None] = relationship()
    assigned_to: Mapped[User | None] = relationship(foreign_keys=[assigned_to_user_id])
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_user_id])
