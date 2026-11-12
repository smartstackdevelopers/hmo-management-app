"""F6.5 Room Occupancy models — counts only; no video/biometric storage."""

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


class RoomOccupancyApprovalGate(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Organisation privacy approval gate. Live cameras stay disabled until complete."""

    __tablename__ = "room_occupancy_approval_gates"
    __table_args__ = (
        UniqueConstraint("organisation_id", name="uq_room_occupancy_approval_gates_org"),
        CheckConstraint(
            "feasibility_status IN ('not_started', 'in_progress', 'completed', 'approved', 'rejected')",
            name="ck_ro_gate_feasibility",
        ),
        CheckConstraint(
            "dpia_status IN ('not_started', 'in_progress', 'completed', 'approved', 'rejected')",
            name="ck_ro_gate_dpia",
        ),
        CheckConstraint(
            "signage_status IN ('not_started', 'in_progress', 'completed', 'approved', 'rejected')",
            name="ck_ro_gate_signage",
        ),
        CheckConstraint(
            "retention_policy_status IN ('not_started', 'in_progress', 'completed', 'approved', 'rejected')",
            name="ck_ro_gate_retention",
        ),
        CheckConstraint(
            "camera_compatibility_status IN ('not_started', 'in_progress', 'completed', 'approved', 'rejected')",
            name="ck_ro_gate_camera",
        ),
    )

    feasibility_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    dpia_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    signage_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    retention_policy_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    camera_compatibility_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    approved_room_purposes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    authorised_viewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    accuracy_requirements_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    documentation_refs: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    approval_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    live_counting_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class RoomOccupancySettings(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Configurable occupancy thresholds and retention (days)."""

    __tablename__ = "room_occupancy_settings"
    __table_args__ = (UniqueConstraint("organisation_id", name="uq_room_occupancy_settings_org"),)

    near_capacity_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    offline_after_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    history_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    alert_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)


class OccupancyCountingDevice(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Registered edge/camera counting device. Credentials encrypted; never returned to clients."""

    __tablename__ = "occupancy_counting_devices"
    __table_args__ = (
        UniqueConstraint("organisation_id", "device_key", name="uq_occupancy_devices_org_key"),
        Index("ix_occupancy_devices_org_room", "organisation_id", "room_id"),
        CheckConstraint(
            "device_type IN ('edge_people_counter', 'onvif_camera', 'rtsp_camera', 'sensor')",
            name="ck_occupancy_device_type",
        ),
        CheckConstraint(
            "connection_status IN ('pending', 'online', 'offline', 'error', 'disabled', 'incompatible')",
            name="ck_occupancy_device_connection",
        ),
    )

    device_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    device_type: Mapped[str] = mapped_column(String(32), nullable=False)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True
    )
    supports_people_counting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    compatibility_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stream_activation_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    last_communication_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    credentials_meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class RoomOccupancyState(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Current estimated occupancy for a room (count only)."""

    __tablename__ = "room_occupancy_states"
    __table_args__ = (
        UniqueConstraint("organisation_id", "room_id", name="uq_room_occupancy_states_org_room"),
        Index("ix_room_occupancy_states_status", "organisation_id", "occupancy_status"),
        CheckConstraint(
            "occupancy_status IN ('available', 'occupied', 'near_capacity', 'at_capacity', 'offline')",
            name="ck_room_occupancy_status",
        ),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    estimated_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    occupancy_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occupancy_status: Mapped[str] = mapped_column(String(32), nullable=False, default="offline")
    is_manual_correction: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("occupancy_counting_devices.id", ondelete="SET NULL"), nullable=True
    )
    device_connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default="offline")
    last_count_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="none")


class RoomOccupancyCountHistory(UUIDPrimaryKeyMixin, OrganisationScopedMixin, Base):
    """Historical count records only — no imagery or identity."""

    __tablename__ = "room_occupancy_count_history"
    __table_args__ = (
        Index("ix_room_occ_hist_org_room_at", "organisation_id", "room_id", "recorded_at"),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("occupancy_counting_devices.id", ondelete="SET NULL"), nullable=True
    )
    estimated_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    occupancy_status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="edge")
    is_manual_correction: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)


class RoomOccupancyManualCorrection(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Audit trail for manual count corrections — retains previous estimate."""

    __tablename__ = "room_occupancy_manual_corrections"
    __table_args__ = (Index("ix_room_occ_corr_org_room", "organisation_id", "room_id"),)

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    previous_estimated_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    corrected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class RoomOccupancyAlert(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Capacity / offline alerts with active-condition dedupe."""

    __tablename__ = "room_occupancy_alerts"
    __table_args__ = (
        Index("ix_room_occ_alerts_org_status", "organisation_id", "status"),
        UniqueConstraint(
            "organisation_id",
            "room_id",
            "alert_category",
            "dedupe_key",
            name="uq_room_occ_alerts_active_dedupe",
        ),
        CheckConstraint(
            "alert_category IN ("
            "'at_capacity', 'near_capacity', 'device_offline', 'missing_updates', 'connection_failure'"
            ")",
            name="ck_room_occ_alert_category",
        ),
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="ck_room_occ_alert_severity",
        ),
        CheckConstraint(
            "status IN ('active', 'acknowledged', 'resolved')",
            name="ck_room_occ_alert_status",
        ),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("occupancy_counting_devices.id", ondelete="SET NULL"), nullable=True
    )
    alert_category: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    estimated_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
