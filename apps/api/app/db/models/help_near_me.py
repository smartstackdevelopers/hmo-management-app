"""F5.2 Help Near Me report and short-lived search rate-limit events."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


REPORT_REASONS = frozenset(
    {
        "service_closed",
        "address_incorrect",
        "opening_hours_incorrect",
        "contact_incorrect",
        "eligibility_incorrect",
        "information_outdated",
        "cannot_locate",
        "other",
    }
)
REPORT_STATUSES = frozenset(
    {
        "submitted",
        "under_review",
        "information_confirmed",
        "listing_updated",
        "reverified",
        "rejected",
        "closed",
    }
)


class CommunityServiceOutdatedReport(
    UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base
):
    __tablename__ = "community_service_outdated_reports"
    __table_args__ = (
        CheckConstraint(
            "reason IN ("
            "'service_closed', 'address_incorrect', 'opening_hours_incorrect', "
            "'contact_incorrect', 'eligibility_incorrect', 'information_outdated', "
            "'cannot_locate', 'other'"
            ")",
            name="ck_cs_outdated_reports_reason",
        ),
        CheckConstraint(
            "status IN ("
            "'submitted', 'under_review', 'information_confirmed', "
            "'listing_updated', 'reverified', 'rejected', 'closed'"
            ")",
            name="ck_cs_outdated_reports_status",
        ),
        Index("ix_cs_outdated_reports_org_status", "organisation_id", "status"),
        Index("ix_cs_outdated_reports_service_created", "service_id", "created_at"),
        Index("ix_cs_outdated_reports_reporter_created", "reporter_user_id", "created_at"),
    )

    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_services.id", ondelete="CASCADE"),
        nullable=False,
    )
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="submitted",
        server_default="submitted",
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HelpNearMeSearchEvent(UUIDPrimaryKeyMixin, OrganisationScopedMixin, Base):
    """Ephemeral postcode search counters for rate limiting — not a location history product."""

    __tablename__ = "help_near_me_search_events"
    __table_args__ = (
        Index("ix_help_near_me_search_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    postcode_normalised: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
