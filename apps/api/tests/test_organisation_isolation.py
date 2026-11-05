"""Organisation isolation and membership tests.

PostgreSQL tests require DATABASE_URL / TEST_DATABASE_URL.
Mocked HTTP tests use dependency overrides (not a live Auth0 tenant).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Organisation, OrganisationMembership, Property, User
from app.db.models.enums import HMoreRole, MembershipStatus
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context
from app.tenancy import isolation as iso
from app.tenancy.jobs import JobOrganisationContext, validate_job_organisation_context
from app.tenancy.membership_service import (
    set_membership_status,
    user_may_access_organisation,
)
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def _authz_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        external_subject=f"auth0|{uuid.uuid4()}",
        email=f"{uuid.uuid4().hex}@example.com",
        display_name="Isolation User",
        authorization_version=1,
    )


def _org_ctx(role: HMoreRole, organisation_id: uuid.UUID) -> OrganisationContext:
    user = _authz_user()
    authz = AuthorizationContext(
        user=user,  # type: ignore[arg-type]
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
    return OrganisationContext(
        user=user,  # type: ignore[arg-type]
        organisation_id=organisation_id,
        role=role,
        authorization=authz,
    )


def test_missing_organisation_context_rejected_via_api() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/isolation/properties")
    assert response.status_code == 401


def test_foreign_property_id_denied_by_isolation_helper() -> None:
    """IDOR-style access: knowing another org's UUID must not grant access."""
    org_a = uuid.uuid4()
    ctx = _org_ctx(HMoreRole.ORGANISATION_ADMIN, org_a)

    class _FakeSession:
        def get(self, model, ident):  # noqa: ANN001
            return SimpleNamespace(id=ident, organisation_id=uuid.uuid4(), name="Foreign")

    with pytest.raises(HTTPException) as exc:
        iso.require_property_for_org(_FakeSession(), ctx, uuid.uuid4())  # type: ignore[arg-type]
    assert exc.value.status_code == 403


def test_job_payload_requires_organisation_id() -> None:
    with pytest.raises(ValueError, match="organisation_id"):
        JobOrganisationContext.from_payload({})


def test_job_payload_roundtrip() -> None:
    org_id = uuid.uuid4()
    ctx = JobOrganisationContext(organisation_id=org_id, correlation_id="c1")
    again = JobOrganisationContext.from_payload(ctx.to_payload())
    assert again.organisation_id == org_id
    assert again.correlation_id == "c1"


pytestmark_postgres = pytest.mark.postgres


@pytest.mark.postgres
def test_cross_organisation_property_isolation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="Org A", slug=f"org-a-{unique_suffix}")
    org_b = Organisation(name="Org B", slug=f"org-b-{unique_suffix}")
    user_a = User(
        email=f"a-{unique_suffix}@example.com",
        display_name="User A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    user_b = User(
        email=f"b-{unique_suffix}@example.com",
        display_name="User B",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, user_a, user_b])
    db_session.flush()

    db_session.add_all(
        [
            OrganisationMembership(
                user_id=user_a.id,
                organisation_id=org_a.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=user_b.id,
                organisation_id=org_b.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    prop_a = Property(
        organisation_id=org_a.id,
        name="A House",
        address_line1="1 A Street",
        city="London",
        postcode="E1 1AA",
    )
    prop_b = Property(
        organisation_id=org_b.id,
        name="B House",
        address_line1="1 B Street",
        city="London",
        postcode="E2 2BB",
    )
    db_session.add_all([prop_a, prop_b])
    db_session.flush()
    prop_a_id = prop_a.id
    prop_b_id = prop_b.id
    org_a_id = org_a.id
    org_b_id = org_b.id

    ctx_a = OrganisationContext(
        user=user_a,
        organisation_id=org_a_id,
        role=HMoreRole.ORGANISATION_ADMIN,
        authorization=AuthorizationContext(
            user=user_a,
            memberships=[],
            active_organisation_id=org_a_id,
            active_role=HMoreRole.ORGANISATION_ADMIN,
        ),
    )
    ctx_b = OrganisationContext(
        user=user_b,
        organisation_id=org_b_id,
        role=HMoreRole.ORGANISATION_ADMIN,
        authorization=AuthorizationContext(
            user=user_b,
            memberships=[],
            active_organisation_id=org_b_id,
            active_role=HMoreRole.ORGANISATION_ADMIN,
        ),
    )

    apply_organisation_rls(db_session, org_a_id)
    db_session.expire_all()
    listed_a = iso.list_properties_for_org(db_session, ctx_a)
    assert {row.id for row in listed_a} == {prop_a_id}
    assert iso.get_property_for_org(db_session, ctx_a, prop_b_id) is None
    with pytest.raises(HTTPException) as read_exc:
        iso.require_property_for_org(db_session, ctx_a, prop_b_id)
    assert read_exc.value.status_code == 403
    with pytest.raises(HTTPException):
        iso.update_property_for_org(db_session, ctx_a, prop_b_id, name="hacked")
    with pytest.raises(HTTPException):
        iso.delete_property_for_org(db_session, ctx_a, prop_b_id)

    apply_organisation_rls(db_session, org_b_id)
    db_session.expire_all()
    listed_b = iso.list_properties_for_org(db_session, ctx_b)
    assert {row.id for row in listed_b} == {prop_b_id}
    assert iso.get_property_for_org(db_session, ctx_b, prop_a_id) is None


@pytest.mark.postgres
def test_inactive_membership_denied(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Org", slug=f"org-inactive-{unique_suffix}")
    user = User(
        email=f"inactive-{unique_suffix}@example.com",
        display_name="Inactive",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, user])
    db_session.flush()
    membership = OrganisationMembership(
        user_id=user.id,
        organisation_id=org.id,
        role=HMoreRole.TENANT,
        status=MembershipStatus.SUSPENDED,
    )
    db_session.add(membership)
    db_session.flush()
    assert not user_may_access_organisation(
        db_session, user=user, organisation_id=org.id, allow_super_admin=False
    )


@pytest.mark.postgres
def test_unauthorized_self_activation_rejected(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Org", slug=f"org-self-{unique_suffix}")
    user = User(
        email=f"self-{unique_suffix}@example.com",
        display_name="Self",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, user])
    db_session.flush()
    membership = OrganisationMembership(
        user_id=user.id,
        organisation_id=org.id,
        role=HMoreRole.TENANT,
        status=MembershipStatus.SUSPENDED,
    )
    db_session.add(membership)
    db_session.flush()
    actor = AuthorizationContext(
        user=user,
        memberships=[
            MembershipView(
                membership_id=membership.id,
                role=HMoreRole.TENANT,
                organisation_id=org.id,
                status=MembershipStatus.SUSPENDED,
            )
        ],
        active_organisation_id=org.id,
        active_role=HMoreRole.TENANT,
    )
    with pytest.raises(HTTPException) as exc:
        set_membership_status(
            db_session,
            actor=actor,
            membership_id=membership.id,
            status=MembershipStatus.ACTIVE,
        )
    assert exc.value.status_code == 403


@pytest.mark.postgres
def test_job_actor_must_belong_to_organisation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Org", slug=f"org-job-{unique_suffix}")
    user = User(
        email=f"job-{unique_suffix}@example.com",
        display_name="Job",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, user])
    db_session.flush()
    with pytest.raises(PermissionError):
        validate_job_organisation_context(
            db_session,
            {
                "organisation_id": str(org.id),
                "actor_user_id": str(user.id),
            },
        )


@pytest.mark.postgres
def test_job_requires_actor_and_existing_organisation(
    db_session: Session, unique_suffix: str
) -> None:
    apply_platform_rls_bypass(db_session)
    with pytest.raises(ValueError, match="Organisation not found"):
        validate_job_organisation_context(
            db_session,
            {"organisation_id": str(uuid.uuid4()), "actor_user_id": str(uuid.uuid4())},
        )
    org = Organisation(name="Org Job Req", slug=f"org-job-req-{unique_suffix}")
    db_session.add(org)
    db_session.flush()
    with pytest.raises(PermissionError, match="actor_user_id"):
        validate_job_organisation_context(
            db_session,
            {"organisation_id": str(org.id)},
        )


@pytest.mark.postgres
def test_create_property_stamps_trusted_organisation_only(
    db_session: Session, unique_suffix: str
) -> None:
    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="Create A", slug=f"create-a-{unique_suffix}")
    org_b = Organisation(name="Create B", slug=f"create-b-{unique_suffix}")
    user = User(
        email=f"create-{unique_suffix}@example.com",
        display_name="Creator",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, user])
    db_session.flush()
    ctx = OrganisationContext(
        user=user,
        organisation_id=org_a.id,
        role=HMoreRole.LANDLORD,
        authorization=AuthorizationContext(
            user=user,
            memberships=[],
            active_organisation_id=org_a.id,
            active_role=HMoreRole.LANDLORD,
        ),
    )
    apply_organisation_rls(db_session, org_a.id)
    created = iso.create_property_for_org(
        db_session,
        ctx,
        name="Scoped",
        address_line1="1 Street",
        city="London",
        postcode="E1 1AA",
    )
    assert created.organisation_id == org_a.id
    assert created.organisation_id != org_b.id


@pytest.mark.postgres
def test_rls_hides_foreign_rows_without_app_filter(db_session: Session, unique_suffix: str) -> None:
    """Direct SQLAlchemy get still sees PK rows; list queries under RLS hide foreign orgs."""
    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="RLS A", slug=f"rls-a-{unique_suffix}")
    org_b = Organisation(name="RLS B", slug=f"rls-b-{unique_suffix}")
    db_session.add_all([org_a, org_b])
    db_session.flush()
    prop_a = Property(
        organisation_id=org_a.id,
        name="RLS A Prop",
        address_line1="1",
        city="London",
        postcode="N1 1AA",
    )
    prop_b = Property(
        organisation_id=org_b.id,
        name="RLS B Prop",
        address_line1="2",
        city="London",
        postcode="N2 2BB",
    )
    db_session.add_all([prop_a, prop_b])
    db_session.flush()
    prop_a_id = prop_a.id
    org_a_id = org_a.id

    apply_organisation_rls(db_session, org_a_id)
    db_session.expire_all()
    from sqlalchemy import select

    visible = list(db_session.scalars(select(Property)))
    assert {row.id for row in visible} == {prop_a_id}
