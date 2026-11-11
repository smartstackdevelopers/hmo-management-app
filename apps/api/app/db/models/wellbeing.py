"""F5.5 tenant wellbeing: private check-ins, routines and org resource libraries."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class WellbeingCheckin(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "wellbeing_checkins"
    __table_args__ = (
        UniqueConstraint("tenant_id", "checkin_date", name="uq_wellbeing_checkins_tenant_date"),
        CheckConstraint(
            "mood IS NULL OR mood IN ('very_good', 'good', 'okay', 'low', 'very_low')",
            name="ck_wellbeing_checkins_mood",
        ),
        CheckConstraint(
            "energy_level IS NULL OR (energy_level >= 1 AND energy_level <= 5)",
            name="ck_wellbeing_checkins_energy",
        ),
        CheckConstraint(
            "stress_level IS NULL OR (stress_level >= 1 AND stress_level <= 5)",
            name="ck_wellbeing_checkins_stress",
        ),
        Index("ix_wellbeing_checkins_org_tenant_date", "organisation_id", "tenant_id", "checkin_date"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False)
    mood: Mapped[str | None] = mapped_column(String(32), nullable=True)
    energy_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class WellbeingRoutine(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "wellbeing_routines"
    __table_args__ = (
        CheckConstraint(
            "recurrence IN ('daily', 'weekdays', 'weekly', 'one_time')",
            name="ck_wellbeing_routines_recurrence",
        ),
        Index("ix_wellbeing_routines_org_tenant_active", "organisation_id", "tenant_id", "is_active"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="other", server_default="other")
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    recurrence: Mapped[str] = mapped_column(String(32), nullable=False, default="daily", server_default="daily")
    weekday_mask: Mapped[int | None] = mapped_column(Integer, nullable=True)
    one_time_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    reminder_minutes_before: Mapped[int | None] = mapped_column(Integer, nullable=True)


class WellbeingRoutineCompletion(UUIDPrimaryKeyMixin, OrganisationScopedMixin, Base):
    __tablename__ = "wellbeing_routine_completions"
    __table_args__ = (
        UniqueConstraint("routine_id", "activity_date", name="uq_wellbeing_routine_completions_day"),
        CheckConstraint("status IN ('completed', 'skipped')", name="ck_wellbeing_routine_completions_status"),
        Index("ix_wellbeing_routine_completions_org_tenant_date", "organisation_id", "tenant_id", "activity_date"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    routine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wellbeing_routines.id", ondelete="CASCADE"), nullable=False
    )
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WellbeingResource(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "wellbeing_resources"
    __table_args__ = (
        CheckConstraint("kind IN ('exercise', 'mindfulness')", name="ck_wellbeing_resources_kind"),
        CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'rejected')",
            name="ck_wellbeing_resources_verification",
        ),
        Index("ix_wellbeing_resources_org_kind_active", "organisation_id", "kind", "is_active"),
    )

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activity_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    equipment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    safety_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified", server_default="unverified")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class WellbeingSavedResource(UUIDPrimaryKeyMixin, OrganisationScopedMixin, Base):
    __tablename__ = "wellbeing_saved_resources"
    __table_args__ = (
        UniqueConstraint("tenant_id", "resource_id", name="uq_wellbeing_saved_resources_tenant_resource"),
        Index("ix_wellbeing_saved_resources_org_tenant", "organisation_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wellbeing_resources.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WellbeingResourceCompletion(UUIDPrimaryKeyMixin, OrganisationScopedMixin, Base):
    __tablename__ = "wellbeing_resource_completions"
    __table_args__ = (
        CheckConstraint("status IN ('completed', 'stopped')", name="ck_wellbeing_resource_completions_status"),
        Index("ix_wellbeing_resource_completions_org_tenant", "organisation_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wellbeing_resources.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed", server_default="completed")
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WellbeingDirectoryEntry(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "wellbeing_directory_entries"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'rejected')",
            name="ck_wellbeing_directory_verification",
        ),
        Index("ix_wellbeing_directory_org_active", "organisation_id", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eligibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    referral_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    community_service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("community_services.id", ondelete="SET NULL"), nullable=True
    )
    is_clinical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified", server_default="unverified")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
