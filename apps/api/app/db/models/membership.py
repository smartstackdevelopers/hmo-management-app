from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import (
    HMoreRole,
    MembershipStatus,
    hmore_role_enum,
    membership_status_enum,
)
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.organisation import Organisation
    from app.db.models.user import User


class OrganisationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Links a user to an organisation with exactly one of the six HMore roles.

    Super Admin is platform-scoped: organisation_id must be NULL.
    Every other role requires an organisation_id.
    """

    __tablename__ = "organisation_memberships"
    __table_args__ = (
        CheckConstraint(
            "(role = 'super_admin' AND organisation_id IS NULL) "
            "OR (role <> 'super_admin' AND organisation_id IS NOT NULL)",
            name="ck_membership_super_admin_org_scope",
        ),
        UniqueConstraint(
            "user_id",
            "organisation_id",
            name="uq_membership_user_organisation",
        ),
        Index(
            "uq_membership_one_super_admin_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("role = 'super_admin'"),
        ),
        Index("ix_memberships_organisation_role", "organisation_id", "role"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    role: Mapped[HMoreRole] = mapped_column(hmore_role_enum, nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        membership_status_enum,
        nullable=False,
        default=MembershipStatus.ACTIVE,
        server_default=MembershipStatus.ACTIVE.value,
    )

    user: Mapped[User] = relationship(back_populates="memberships")
    organisation: Mapped[Organisation | None] = relationship(
        back_populates="memberships"
    )
