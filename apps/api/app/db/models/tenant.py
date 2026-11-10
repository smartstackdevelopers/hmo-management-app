from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import RecordStatus, record_status_enum
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.organisation import Organisation
    from app.db.models.property import Property
    from app.db.models.room import Room
    from app.db.models.user import User


class Tenant(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Organisation-owned tenant person record for Phase 1 baseline CRUD (F1.6).

    Distinct from the Tenant login role on memberships. A tenant person may exist
    before they receive a user identity.
    """

    __tablename__ = "tenants"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    preferred_name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tenancy_reference: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    consent_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RecordStatus] = mapped_column(
        record_status_enum,
        nullable=False,
        default=RecordStatus.ACTIVE,
        server_default=RecordStatus.ACTIVE.value,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    organisation: Mapped[Organisation] = relationship(back_populates="tenants")
    user: Mapped[User | None] = relationship(back_populates="tenant_profiles")
    assigned_property: Mapped[Property | None] = relationship(foreign_keys=[assigned_property_id])
    assigned_room: Mapped[Room | None] = relationship(foreign_keys=[assigned_room_id])
