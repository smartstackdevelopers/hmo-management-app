"""Organisation directory list (Super Admin)."""

from __future__ import annotations

import uuid

import pytest

from app.db.models import Organisation, User
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.membership import OrganisationMembership
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.membership_service import list_organisations_directory
from app.tenancy.session_rls import apply_platform_rls_bypass

pytestmark = pytest.mark.postgres


def _super_authz(user: User) -> AuthorizationContext:
    return AuthorizationContext(
        user=user,
        memberships=[
            MembershipView(
                membership_id=uuid.uuid4(),
                role=HMoreRole.SUPER_ADMIN,
                organisation_id=None,
                status=MembershipStatus.ACTIVE,
            )
        ],
        active_organisation_id=None,
        active_role=HMoreRole.SUPER_ADMIN,
    )


def test_list_organisations_directory_super_admin(db_session, unique_suffix: str) -> None:
    org = Organisation(name=f"Listed Org {unique_suffix}", slug=f"listed-{unique_suffix}")
    db_session.add(org)
    user = User(
        external_subject=f"auth0|org-list-{unique_suffix}",
        email=f"org-list-sa-{unique_suffix}@example.com",
        display_name="Org List SA",
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=user.id,
            organisation_id=None,
            role=HMoreRole.SUPER_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    apply_platform_rls_bypass(db_session)
    rows = list_organisations_directory(db_session, actor=_super_authz(user))
    ids = {row["id"] for row in rows}
    assert str(org.id) in ids