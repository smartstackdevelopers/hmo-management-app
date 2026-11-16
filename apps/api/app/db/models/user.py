from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import AccountStatus, account_status_enum
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.membership import OrganisationMembership
    from app.db.models.tenant import Tenant


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Platform identity record.

    Roles are not stored on this table. Role assignment lives on
    organisation_memberships so identity, membership, and permissions stay separate.
    Native auth (Prompt 12) adds password hash + account lifecycle status.
    """

    __tablename__ = "users"

    external_subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        comment="Stable subject (native hmore|{user_id} or legacy IdP sub).",
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_status: Mapped[AccountStatus] = mapped_column(
        account_status_enum,
        nullable=False,
        default=AccountStatus.APPROVED,
        server_default=AccountStatus.APPROVED.value,
        comment="pending until registration approval; approved users may login.",
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    authorization_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Incremented when role memberships change so clients refresh authz state.",
    )

    memberships: Mapped[list[OrganisationMembership]] = relationship(
        back_populates="user"
    )
    tenant_profiles: Mapped[list[Tenant]] = relationship(back_populates="user")
