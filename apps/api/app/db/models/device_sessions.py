"""F4.6 mobile device sessions. Biometric templates are never stored here."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class MobileDeviceSession(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """One authenticated installation for one user.

    ``installation_id`` is a client-generated UUID. A revoked or lost row cannot
    be turned active again. The client must create a new installation id after
    a full Auth0 login. This table does not store fingerprints, face data, or tokens.
    """

    __tablename__ = "mobile_device_sessions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "installation_id",
            name="uq_mobile_device_sessions_user_installation",
        ),
        CheckConstraint(
            "platform IN ('ios', 'android', 'web')",
            name="ck_mobile_device_sessions_platform",
        ),
        CheckConstraint(
            "status IN ('active', 'revoked', 'lost')",
            name="ck_mobile_device_sessions_status",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    installation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
