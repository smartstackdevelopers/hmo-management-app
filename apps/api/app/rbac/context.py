"""Server-side authorization context loaded from memberships, never from the client."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.membership import OrganisationMembership
from app.db.models.user import User
from app.rbac.matrix import permissions_for_role
from app.rbac.permissions import Permission


@dataclass(frozen=True)
class MembershipView:
    membership_id: uuid.UUID
    role: HMoreRole
    organisation_id: uuid.UUID | None
    status: MembershipStatus


@dataclass
class AuthorizationContext:
    user: User
    memberships: list[MembershipView] = field(default_factory=list)
    active_organisation_id: uuid.UUID | None = None
    active_role: HMoreRole | None = None

    @property
    def authorization_version(self) -> int:
        return getattr(self.user, "authorization_version", 1) or 1

    def active_membership(self) -> MembershipView | None:
        if self.active_role is None:
            return None
        for membership in self.memberships:
            if membership.status != MembershipStatus.ACTIVE:
                continue
            if membership.role != self.active_role:
                continue
            if membership.role == HMoreRole.SUPER_ADMIN:
                return membership
            if membership.organisation_id == self.active_organisation_id:
                return membership
        return None

    def permissions(self) -> frozenset[Permission]:
        membership = self.active_membership()
        if membership is None:
            return frozenset()
        return permissions_for_role(membership.role)

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions()

    def has_role(self, role: HMoreRole) -> bool:
        return any(
            m.role == role and m.status == MembershipStatus.ACTIVE for m in self.memberships
        )


def membership_views(rows: list[OrganisationMembership]) -> list[MembershipView]:
    return [
        MembershipView(
            membership_id=row.id,
            role=row.role,
            organisation_id=row.organisation_id,
            status=row.status,
        )
        for row in rows
    ]
