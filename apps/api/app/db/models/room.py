from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import RecordStatus, record_status_enum
from app.db.models.mixins import OrganisationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.property import Property


class Room(UUIDPrimaryKeyMixin, OrganisationScopedMixin, TimestampMixin, Base):
    """Room within a property. organisation_id mirrors the parent property for F1.5 queries."""

    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint(
            "property_id",
            "label",
            name="uq_rooms_property_label",
        ),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    floor_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    room_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    max_occupancy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[RecordStatus] = mapped_column(
        record_status_enum,
        nullable=False,
        default=RecordStatus.ACTIVE,
        server_default=RecordStatus.ACTIVE.value,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    housing_property: Mapped[Property] = relationship(back_populates="rooms")
