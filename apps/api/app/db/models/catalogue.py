"""Organisation catalogues for published community services and opportunities (F4.1).

No rows are seeded. An empty catalogue is a valid state.
"""

from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CommunityService(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "community_services"
    __table_args__ = (
        CheckConstraint(
            "category IN ('food_bank', 'kitchen', 'clothing_bank', 'local_service')",
            name="ck_community_services_category",
        ),
        Index("ix_community_services_org_published", "organisation_id", "is_published"),
    )

    category: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_line: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eligibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
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
