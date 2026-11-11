"""Organisation catalogues for published community services and opportunities.

F4.1 introduced the base tables. F5.1 extends community services with
verification workflow fields and a verification history table.

No rows are seeded. An empty catalogue is a valid state.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


VERIFICATION_STATUSES = frozenset(
    {
        "pending_verification",
        "verified",
        "needs_review",
        "outdated",
        "inactive",
    }
)
CLOTHING_SERVICE_TYPES = frozenset({"provides_clothing", "accepts_donations", "both"})


class CommunityService(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "community_services"
    __table_args__ = (
        CheckConstraint(
            "category IN ('food_bank', 'kitchen', 'clothing_bank', 'local_service')",
            name="ck_community_services_category",
        ),
        CheckConstraint(
            "verification_status IN ("
            "'pending_verification', 'verified', 'needs_review', 'outdated', 'inactive'"
            ")",
            name="ck_community_services_verification_status",
        ),
        CheckConstraint(
            "clothing_service_type IS NULL OR clothing_service_type IN ("
            "'provides_clothing', 'accepts_donations', 'both'"
            ")",
            name="ck_community_services_clothing_service_type",
        ),
        Index("ix_community_services_org_published", "organisation_id", "is_published"),
        Index(
            "ix_community_services_org_category_status",
            "organisation_id",
            "category",
            "verification_status",
        ),
    )

    category: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_line: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opening_days: Mapped[str | None] = mapped_column(Text, nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eligibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    referral_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    clothing_service_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending_verification",
        server_default="pending_verification",
    )
    information_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class CommunityServiceVerificationEvent(UUIDPrimaryKeyMixin, OrganisationScopedMixin, Base):
    """Immutable verification / status change history for a community service."""

    __tablename__ = "community_service_verification_events"
    __table_args__ = (
        CheckConstraint(
            "to_status IN ("
            "'pending_verification', 'verified', 'needs_review', 'outdated', 'inactive'"
            ")",
            name="ck_cs_verification_events_to_status",
        ),
        Index(
            "ix_cs_verification_events_service_created",
            "service_id",
            "created_at",
        ),
    )

    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_services.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class OpportunityListing(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "opportunity_listings"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('job', 'training')",
            name="ck_opportunity_listings_kind",
        ),
        Index("ix_opportunity_listings_org_kind_published", "organisation_id", "kind", "is_published"),
    )

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
