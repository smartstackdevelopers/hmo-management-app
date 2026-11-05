"""FastAPI authorization dependencies built on F1.3 authentication."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.tokens import http_403
from app.db.models import OrganisationMembership, User
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.session import get_session
from app.rbac.context import AuthorizationContext, MembershipView, membership_views
from app.rbac.permissions import Permission, parse_permission
from app.rbac.service import require_permission


def get_authorization_context(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    x_organisation_id: Annotated[str | None, Header(alias="X-Organisation-Id")] = None,
    x_hmore_role: Annotated[str | None, Header(alias="X-HMore-Role")] = None,
) -> AuthorizationContext:
    """Build authz context from DB memberships.

    Optional headers select among the caller's *existing* memberships only.
    Client-supplied roles/orgs that are not assigned are rejected.
    """
    rows = list(
        session.scalars(
            select(OrganisationMembership).where(OrganisationMembership.user_id == user.id)
        )
    )
    views = membership_views(rows)
    active = [m for m in views if m.status == MembershipStatus.ACTIVE]
    if not active:
        raise http_403("No active role membership")

    requested_org: uuid.UUID | None = None
    if x_organisation_id:
        try:
            requested_org = uuid.UUID(x_organisation_id)
        except ValueError as exc:
            raise http_403("Invalid X-Organisation-Id") from exc

    requested_role: HMoreRole | None = None
    if x_hmore_role:
        try:
            requested_role = HMoreRole(x_hmore_role)
        except ValueError as exc:
            raise http_403("Unknown role in X-HMore-Role") from exc

    selected = _select_membership(active, requested_org, requested_role)
    return AuthorizationContext(
        user=user,
        memberships=views,
        active_organisation_id=(
            selected.organisation_id
            if selected.role != HMoreRole.SUPER_ADMIN
            else requested_org
        ),
        active_role=selected.role,
    )


def _select_membership(
    active: list[MembershipView],
    requested_org: uuid.UUID | None,
    requested_role: HMoreRole | None,
) -> MembershipView:
    candidates = list(active)
    if requested_role is not None:
        candidates = [m for m in candidates if m.role == requested_role]
        if not candidates:
            raise http_403("Requested role is not assigned to this user")

    if requested_org is not None:
        org_matches = [m for m in candidates if m.organisation_id == requested_org]
        if org_matches:
            return org_matches[0]
        super_matches = [m for m in candidates if m.role == HMoreRole.SUPER_ADMIN]
        if super_matches:
            return super_matches[0]
        raise http_403("Requested organisation is not assigned to this user")

    if len(candidates) == 1:
        return candidates[0]
    for membership in candidates:
        if membership.role == HMoreRole.SUPER_ADMIN:
            return membership
    raise http_403(
        "Multiple memberships found; send X-Organisation-Id and/or X-HMore-Role "
        "matching an assigned membership"
    )


def require_perm(permission: Permission | str):
    required = permission if isinstance(permission, Permission) else parse_permission(permission)

    def _dependency(
        ctx: AuthorizationContext = Depends(get_authorization_context),
    ) -> AuthorizationContext:
        require_permission(ctx, required)
        return ctx

    return _dependency
