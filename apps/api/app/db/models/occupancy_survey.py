"""F1.10 occupancy site-survey records. No camera or CV functionality."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OccupancySiteSurvey(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Organisation-scoped site survey for occupancy feasibility (pre-camera gate)."""

    __tablename__ = "occupancy_site_surveys"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        server_default="draft",
        index=True,
    )
    survey_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    surveyor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    surveyor_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    site_contact_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    building_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    facilities_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    health_safety_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    accessibility_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Proposed gate fields for a future DPIA/camera programme — not a camera system.
    camera_feasibility_notes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    feasibility_status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    feasibility_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OccupancySurveyRoomAssessment(
    UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base
):
    __tablename__ = "occupancy_survey_room_assessments"

    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("occupancy_site_surveys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    room_label: Mapped[str] = mapped_column(String(100), nullable=False)
    assessment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class OccupancySurveyFinding(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "occupancy_survey_findings"

    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("occupancy_site_surveys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
    )
    responsible_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="open",
        server_default="open",
        index=True,
    )
    evidence_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_metadata.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
