"""CLI bootstrap helpers for Auth0-first onboarding."""

from __future__ import annotations

import pytest

from app.db.models import OrganisationMembership, User
from app.db.models.enums import HMoreRole
from app.ops.identity_bootstrap import (
    BootstrapError,
    describe_user,
    get_or_create_organisation,
    grant_org_role,
    grant_super_admin,
)

pytestmark = pytest.mark.postgres


def test_grant_super_admin_and_org_roles(db_session, unique_suffix: str) -> None:
    email = f"bootstrap-sa-{unique_suffix}@example.com"
    grant_super_admin(db_session, email, display_name="Bootstrap SA")

    info = describe_user(db_session, email)
    assert info["external_subject"] is None
    assert any(m["role"] == "super_admin" for m in info["memberships"])

    tenant_email = f"bootstrap-tenant-{unique_suffix}@example.com"
    org_slug = f"bootstrap-org-{unique_suffix}"
    grant_org_role(
        db_session,
        email=tenant_email,
        role_value="tenant",
        organisation_slug=org_slug,
        organisation_name=f"Bootstrap Org {unique_suffix}",
    )

    tenant_info = describe_user(db_session, tenant_email)
    assert len(tenant_info["memberships"]) == 1
    assert tenant_info["memberships"][0]["role"] == "tenant"

    org = get_or_create_organisation(
        db_session,
        name=f"Bootstrap Org {unique_suffix}",
        slug=org_slug,
    )
    assert org.slug == org_slug


def test_super_admin_requires_null_org(db_session, unique_suffix: str) -> None:
    import uuid

    email = f"bootstrap-bad-{unique_suffix}@example.com"
    user = User(email=email, display_name="Bad")
    db_session.add(user)
    db_session.flush()
    from app.ops.identity_bootstrap import upsert_membership

    with pytest.raises(BootstrapError):
        upsert_membership(
            db_session,
            user=user,
            role=HMoreRole.SUPER_ADMIN,
            organisation_id=uuid.uuid4(),
        )