"""Role assignment security tests. Require PostgreSQL when DATABASE_URL is set."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.enums import HMoreRole, MembershipStatus
from app.rbac.assignment import assign_membership
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.permissions import Permission


pytestmark = pytest.mark.postgres


def _make_user(session: Session, suffix: str) -> User:
    user = User(
        external_subject=f"auth0|{uuid.uuid4()}",
        email=f"rbac-{suffix}-{uuid.uuid4().hex[:6]}@example.com",
        display_name=f"RBAC {suffix}",
        authorization_version=1,
    )
    session.add(user)
    session.flush()
    return user


def _make_org(session: Session, suffix: str) -> Organisation:
    org = Organisation(name=f"Org {suffix}-{uuid.uuid4().hex[:6]}", slug=f"org-{uuid.uuid4().hex[:8]}")
    session.add(org)
    session.flush()
    return org


def _actor(
    user: User,
    role: HMoreRole,
    organisation_id: uuid.UUID | None,
) -> AuthorizationContext:
    return AuthorizationContext(
        user=user,
        memberships=[
            MembershipView(
                membership_id=uuid.uuid4(),
                role=role,
                organisation_id=organisation_id,
                status=MembershipStatus.ACTIVE,
            )
        ],
        active_organisation_id=organisation_id,
        active_role=role,
    )


def test_unknown_role_assignment_rejected(db_session: Session, unique_suffix: str) -> None:
    admin = _make_user(db_session, "sa")
    target = _make_user(db_session, "t")
    actor = _actor(admin, HMoreRole.SUPER_ADMIN, None)
    with pytest.raises(ValueError, match="Unknown role"):
        assign_membership(
            db_session,
            actor=actor,
            target_user_id=target.id,
            role_value="council_officer",
            organisation_id=None,
        )


def test_org_admin_cannot_assign_super_admin(db_session: Session, unique_suffix: str) -> None:
    org = _make_org(db_session, unique_suffix)
    admin = _make_user(db_session, "oa")
    target = _make_user(db_session, "t")
    db_session.add(
        OrganisationMembership(
            user_id=admin.id,
            organisation_id=org.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    actor = _actor(admin, HMoreRole.ORGANISATION_ADMIN, org.id)
    with pytest.raises(HTTPException) as exc:
        assign_membership(
            db_session,
            actor=actor,
            target_user_id=target.id,
            role_value=HMoreRole.SUPER_ADMIN.value,
            organisation_id=None,
        )
    assert exc.value.status_code == 403


def test_tenant_cannot_self_escalate(db_session: Session, unique_suffix: str) -> None:
    org = _make_org(db_session, unique_suffix)
    tenant = _make_user(db_session, "tenant")
    db_session.add(
        OrganisationMembership(
            user_id=tenant.id,
            organisation_id=org.id,
            role=HMoreRole.TENANT,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    actor = _actor(tenant, HMoreRole.TENANT, org.id)
    assert not actor.has_permission(Permission.ROLE_ASSIGNMENTS_MANAGE)
    with pytest.raises(HTTPException) as exc:
        assign_membership(
            db_session,
            actor=actor,
            target_user_id=tenant.id,
            role_value=HMoreRole.ORGANISATION_ADMIN.value,
            organisation_id=org.id,
        )
    assert exc.value.status_code == 403


def test_super_admin_assign_bumps_authorization_version(
    db_session: Session, unique_suffix: str
) -> None:
    org = _make_org(db_session, unique_suffix)
    admin = _make_user(db_session, "sa")
    target = _make_user(db_session, "landlord")
    db_session.add(
        OrganisationMembership(
            user_id=admin.id,
            organisation_id=None,
            role=HMoreRole.SUPER_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    before = target.authorization_version
    actor = _actor(admin, HMoreRole.SUPER_ADMIN, None)
    membership = assign_membership(
        db_session,
        actor=actor,
        target_user_id=target.id,
        role_value=HMoreRole.LANDLORD.value,
        organisation_id=org.id,
    )
    assert membership.role == HMoreRole.LANDLORD
    assert target.authorization_version == before + 1
