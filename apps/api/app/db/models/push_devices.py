"""F4.3 Expo push device tokens. One row per installation token, scoped to an organisation."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class PushDeviceToken(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    __tablename__ = "push_device_tokens"
    __table_args__ = (
        UniqueConstraint("expo_push_token", name="uq_push_device_tokens_expo_token"),
        Index("ix_push_device_tokens_org_user_active", "organisation_id", "user_id", "is_active"),
        CheckConstraint(
            "platform IN ('ios', 'android', 'web')",
            name="ck_push_device_tokens_platform",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expo_push_token: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    disabled_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
