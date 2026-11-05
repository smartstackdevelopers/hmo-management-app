"""Secure role-assignment rules. Roles never come from the client as authority."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.tokens import http_403
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.membership import OrganisationMembership
from app.db.models.user import User
from app.rbac.context import AuthorizationContext
from app.rbac.roles import parse_role
from app.rbac.service import require_permission
from app.rbac.permissions import Permission


ORG_ADMIN_ASSIGNABLE = frozenset(
    {
        HMoreRole.ORGANISATION_ADMIN,
        HMoreRole.LANDLORD,
        HMoreRole.TENANT,
        HMoreRole.SUPPORT_WORKER,
        HMoreRole.MAINTENANCE_CONTRACTOR,
    }
)


def bump_authorization_version(session: Session, user: User) -> None:
    current = getattr(user, "authorization_version", 1) or 1
    user.authorization_version = current + 1
    session.add(user)


def assign_membership(
    session: Session,
    *,
    actor: AuthorizationContext,
    target_user_id: uuid.UUID,
    role_value: str,
    organisation_id: uuid.UUID | None,
) -> OrganisationMembership:
    require_permission(actor, Permission.ROLE_ASSIGNMENTS_MANAGE)
    role = parse_role(role_value)

    if role == HMoreRole.SUPER_ADMIN:
        if actor.active_role != HMoreRole.SUPER_ADMIN:
            raise http_403("Only Super Admin may assign Super Admin")
        if organisation_id is not None:
            raise ValueError("Super Admin membership must not include organisation_id")
    else:
        if organisation_id is None:
            raise ValueError("organisation_id is required for non-Super-Admin roles")
        if actor.active_role == HMoreRole.ORGANISATION_ADMIN:
            if role not in ORG_ADMIN_ASSIGNABLE:
                raise http_403("Organisation Admin cannot assign this role")
            if actor.active_organisation_id != organisation_id:
                raise http_403("Cannot assign roles outside your organisation")
        elif actor.active_role == HMoreRole.SUPER_ADMIN:
            pass
        else:
            raise http_403("Not permitted to assign roles")

    # Prevent self-escalation to Super Admin by non-super actors (already blocked above).
    if target_user_id == actor.user.id and role == HMoreRole.SUPER_ADMIN:
        if actor.active_role != HMoreRole.SUPER_ADMIN:
            raise http_403("Cannot grant yourself Super Admin")

    target = session.get(User, target_user_id)
    if target is None:
        raise ValueError("Target user not found")

    if organisation_id is None:
        existing = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.user_id == target_user_id,
                OrganisationMembership.role == HMoreRole.SUPER_ADMIN,
            )
        )
    else:
        existing = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.user_id == target_user_id,
                OrganisationMembership.organisation_id == organisation_id,
            )
        )
    if existing is not None:
        existing.role = role
        existing.status = MembershipStatus.ACTIVE
        membership = existing
    else:
        membership = OrganisationMembership(
            user_id=target_user_id,
            organisation_id=organisation_id,
            role=role,
            status=MembershipStatus.ACTIVE,
        )
        session.add(membership)

    bump_authorization_version(session, target)
    session.flush()
    return membership
