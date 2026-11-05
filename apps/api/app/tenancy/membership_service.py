"""Secure organisation membership operations (extends F1.4 assignment rules)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.tokens import http_403
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.membership import OrganisationMembership
from app.db.models.organisation import Organisation
from app.db.models.user import User
from app.rbac.assignment import ORG_ADMIN_ASSIGNABLE, bump_authorization_version
from app.rbac.context import AuthorizationContext
from app.rbac.permissions import Permission
from app.rbac.service import require_permission


ACTIVE_STATUSES = frozenset({MembershipStatus.ACTIVE})


def require_active_membership(
    session: Session,
    *,
    user_id: uuid.UUID,
    organisation_id: uuid.UUID,
) -> OrganisationMembership:
    membership = session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.user_id == user_id,
            OrganisationMembership.organisation_id == organisation_id,
        )
    )
    if membership is None or membership.status not in ACTIVE_STATUSES:
        raise http_403("No active membership for this organisation")
    return membership


def user_may_access_organisation(
    session: Session,
    *,
    user: User,
    organisation_id: uuid.UUID,
    allow_super_admin: bool = True,
) -> bool:
    if allow_super_admin:
        super_membership = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.user_id == user.id,
                OrganisationMembership.role == HMoreRole.SUPER_ADMIN,
                OrganisationMembership.status == MembershipStatus.ACTIVE,
            )
        )
        if super_membership is not None:
            return True
    membership = session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.user_id == user.id,
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    return membership is not None


def set_membership_status(
    session: Session,
    *,
    actor: AuthorizationContext,
    membership_id: uuid.UUID,
    status: MembershipStatus,
) -> OrganisationMembership:
    """Activate/suspend membership. Callers cannot activate their own unauthorized rows."""
    require_permission(actor, Permission.ROLE_ASSIGNMENTS_MANAGE)

    membership = session.get(OrganisationMembership, membership_id)
    if membership is None:
        raise ValueError("Membership not found")

    if membership.role == HMoreRole.SUPER_ADMIN:
        if actor.active_role != HMoreRole.SUPER_ADMIN:
            raise http_403("Only Super Admin may change Super Admin membership status")
    else:
        if membership.organisation_id is None:
            raise http_403("Invalid membership scope")
        if actor.active_role == HMoreRole.ORGANISATION_ADMIN:
            if actor.active_organisation_id != membership.organisation_id:
                raise http_403("Cannot manage memberships outside your organisation")
            if membership.role not in ORG_ADMIN_ASSIGNABLE:
                raise http_403("Organisation Admin cannot manage this membership")
        elif actor.active_role == HMoreRole.SUPER_ADMIN:
            pass
        else:
            raise http_403("Not permitted to change membership status")

    # Users must not activate themselves into an organisation without admin rights
    # (already enforced by ROLE_ASSIGNMENTS_MANAGE). Extra guard for self-activation:
    if (
        membership.user_id == actor.user.id
        and status == MembershipStatus.ACTIVE
        and membership.status != MembershipStatus.ACTIVE
        and actor.active_role != HMoreRole.SUPER_ADMIN
    ):
        raise http_403("Cannot activate your own membership")

    membership.status = status
    target = session.get(User, membership.user_id)
    if target is not None:
        bump_authorization_version(session, target)
    session.add(membership)
    session.flush()

    from app.audit import events as audit_events
    from app.audit.service import AuditOutcome, record_event

    record_event(
        session,
        action=audit_events.MEMBERSHIP_STATUS_CHANGED,
        resource_type="organisation_membership",
        resource_id=membership.id,
        organisation_id=membership.organisation_id,
        actor_user_id=actor.user.id,
        actor_role=actor.active_role.value if actor.active_role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Membership status changed",
        metadata={
            "target_user_id": str(membership.user_id),
            "status": status.value,
        },
    )
    return membership


def create_organisation(
    session: Session,
    *,
    actor: AuthorizationContext,
    name: str,
    slug: str,
) -> Organisation:
    require_permission(actor, Permission.ORGANISATIONS_CREATE)
    if actor.active_role != HMoreRole.SUPER_ADMIN:
        raise http_403("Only Super Admin may create organisations")
    existing = session.scalar(select(Organisation).where(Organisation.slug == slug))
    if existing is not None:
        raise ValueError("Organisation slug already exists")
    org = Organisation(name=name, slug=slug)
    session.add(org)
    session.flush()

    from app.audit import events as audit_events
    from app.audit.service import AuditOutcome, record_event

    record_event(
        session,
        action=audit_events.ORG_CREATED,
        resource_type="organisation",
        resource_id=org.id,
        organisation_id=org.id,
        actor_user_id=actor.user.id,
        actor_role=actor.active_role.value if actor.active_role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Organisation created",
        metadata={"slug": org.slug},
    )
    return org


def list_memberships_for_organisation(
    session: Session,
    *,
    actor: AuthorizationContext,
    organisation_id: uuid.UUID,
) -> list[OrganisationMembership]:
    require_permission(actor, Permission.ORGANISATION_USERS_READ)
    if actor.active_role == HMoreRole.SUPER_ADMIN:
        pass
    elif actor.active_organisation_id != organisation_id:
        raise http_403("Access denied")
    return list(
        session.scalars(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == organisation_id
            )
        )
    )
