from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.membership import OrganisationMembership
    from app.db.models.tenant import Tenant


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Platform identity record linked later to Auth0 or Entra (F1.3).

    Roles are not stored on this table. Role assignment lives on
    organisation_memberships so identity, membership, and permissions stay separate.
    """

    __tablename__ = "users"

    external_subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        comment="Stable subject from the managed identity provider when F1.3 lands.",
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    memberships: Mapped[list[OrganisationMembership]] = relationship(
        back_populates="user"
    )
    tenant_profiles: Mapped[list[Tenant]] = relationship(back_populates="user")
