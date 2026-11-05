"""Trusted organisation context resolved server-side (never from client claims alone)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.db.models.enums import HMoreRole
from app.db.models.user import User
from app.rbac.context import AuthorizationContext


@dataclass(frozen=True)
class OrganisationContext:
    """Request-scoped organisation boundary after membership validation."""

    user: User
    organisation_id: uuid.UUID
    role: HMoreRole
    authorization: AuthorizationContext
    platform_bypass: bool = False

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id


def from_authorization(
    authz: AuthorizationContext,
    *,
    require_organisation: bool = True,
) -> OrganisationContext | None:
    """Build organisation context from an already-validated AuthorizationContext."""
    if authz.active_role == HMoreRole.SUPER_ADMIN and authz.active_organisation_id is None:
        if require_organisation:
            return None
        return None
    if authz.active_organisation_id is None:
        return None
    if authz.active_role is None:
        return None
    return OrganisationContext(
        user=authz.user,
        organisation_id=authz.active_organisation_id,
        role=authz.active_role,
        authorization=authz,
        platform_bypass=authz.active_role == HMoreRole.SUPER_ADMIN,
    )
