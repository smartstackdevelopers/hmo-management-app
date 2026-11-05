from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import RecordStatus, record_status_enum
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.membership import OrganisationMembership
    from app.db.models.property import Property
    from app.db.models.tenant import Tenant


class Organisation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Housing or support provider that owns isolated operational data."""

    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[RecordStatus] = mapped_column(
        record_status_enum,
        nullable=False,
        default=RecordStatus.ACTIVE,
        server_default=RecordStatus.ACTIVE.value,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    memberships: Mapped[list[OrganisationMembership]] = relationship(
        back_populates="organisation"
    )
    tenants: Mapped[list[Tenant]] = relationship(back_populates="organisation")
    properties: Mapped[list[Property]] = relationship(back_populates="organisation")
