"""F3.15 organisation AI feature flags and configuration history."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OrganisationAiFeatureFlag(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "organisation_ai_feature_flags"
    __table_args__ = (
        UniqueConstraint("organisation_id", "feature_id", name="uq_org_ai_feature_flags_org_feature"),
        Index("ix_org_ai_feature_flags_org", "organisation_id"),
        Index("ix_org_ai_feature_flags_feature", "feature_id"),
        Index("ix_org_ai_feature_flags_org_enabled", "organisation_id", "enabled"),
    )

    feature_id: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pilot_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")


class OrganisationAiFeatureFlagHistory(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Immutable configuration change history."""

    __tablename__ = "organisation_ai_feature_flag_history"
    __table_args__ = (
        Index("ix_org_ai_ff_history_org_feature", "organisation_id", "feature_id", "created_at"),
        Index("ix_org_ai_ff_history_org_created", "organisation_id", "created_at"),
    )

    feature_id: Mapped[str] = mapped_column(String(100), nullable=False)
    flag_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisation_ai_feature_flags.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    previous_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    previous_pilot_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    new_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    new_pilot_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
