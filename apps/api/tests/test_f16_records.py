"""F1.6 tenant/property/room CRUD tests.

PostgreSQL-marked tests require DATABASE_URL. Unit tests cover validation helpers.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.records.schemas import RoomCreate, TenantCreate
from app.tenancy.context import OrganisationContext


def test_tenant_and_property_permissions_in_matrix() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.TENANTS_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.PROPERTIES_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.ROOMS_MANAGE)
    assert role_has_permission(HMoreRole.LANDLORD, Permission.PROPERTIES_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.TENANTS_MANAGE)
    assert role_has_permission(HMoreRole.TENANT, Permission.TENANTS_READ)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.TENANTS_READ)
    assert not role_has_permission(
        HMoreRole.MAINTENANCE_CONTRACTOR, Permission.TENANTS_READ
    )


def test_room_create_rejects_non_positive_capacity() -> None:
    with pytest.raises(Exception):
        RoomCreate(property_id=uuid.uuid4(), label="1A", max_occupancy=0)


def test_tenant_create_requires_preferred_name() -> None:
    with pytest.raises(Exception):
        TenantCreate(preferred_name="")


def test_unauthenticated_crud_returns_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/tenants").status_code == 401
    assert client.get("/api/v1/properties").status_code == 401
    assert client.get("/api/v1/rooms").status_code == 401


def _org_ctx(role: HMoreRole, org_id: uuid.UUID | None = None) -> OrganisationContext:
    organisation_id = org_id or uuid.uuid4()
    user = SimpleNamespace(
        id=uuid.uuid4(),
        authorization_version=1,
        external_subject=f"auth0|{uuid.uuid4()}",
        email="u@example.com",
        display_name="U",
    )
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


@pytest.mark.postgres
def test_cross_org_tenant_property_room_isolation(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, OrganisationMembership, Property, Room, Tenant, User
    from app.records import property_service, room_service, tenant_service
    from app.records.schemas import PropertyCreate, RoomCreate, TenantCreate, TenantUpdate
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="A", slug=f"f16-a-{unique_suffix}")
    org_b = Organisation(name="B", slug=f"f16-b-{unique_suffix}")
    admin_a = User(
        email=f"a-{unique_suffix}@example.com",
        display_name="A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    admin_b = User(
        email=f"b-{unique_suffix}@example.com",
        display_name="B",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, admin_a, admin_b])
    db_session.flush()
    db_session.add_all(
        [
            OrganisationMembership(
                user_id=admin_a.id,
                organisation_id=org_a.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=admin_b.id,
                organisation_id=org_b.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()

    ctx_a = OrganisationContext(
        user=admin_a,
        organisation_id=org_a.id,
        role=HMoreRole.ORGANISATION_ADMIN,
        authorization=AuthorizationContext(
            user=admin_a,
            memberships=[],
            active_organisation_id=org_a.id,
            active_role=HMoreRole.ORGANISATION_ADMIN,
        ),
    )
    ctx_b = OrganisationContext(
        user=admin_b,
        organisation_id=org_b.id,
        role=HMoreRole.ORGANISATION_ADMIN,
        authorization=AuthorizationContext(
            user=admin_b,
            memberships=[],
            active_organisation_id=org_b.id,
            active_role=HMoreRole.ORGANISATION_ADMIN,
        ),
    )

    apply_organisation_rls(db_session, org_a.id)
    tenant_a = tenant_service.create_tenant(
        db_session, ctx_a, TenantCreate(preferred_name="Ada")
    )
    prop_a = property_service.create_property(
        db_session,
        ctx_a,
        PropertyCreate(
            name="House A",
            address_line1="1 A",
            city="London",
            postcode="E1 1AA",
        ),
    )
    room_a = room_service.create_room(
        db_session,
        ctx_a,
        RoomCreate(property_id=prop_a.id, label="A1", max_occupancy=2),
    )
    tenant_a_id, prop_a_id, room_a_id = tenant_a.id, prop_a.id, room_a.id

    apply_organisation_rls(db_session, org_b.id)
    db_session.expire_all()
    with pytest.raises(HTTPException) as exc:
        tenant_service.get_tenant(db_session, ctx_b, tenant_a_id)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException):
        property_service.get_property(db_session, ctx_b, prop_a_id)
    with pytest.raises(HTTPException):
        room_service.get_room(db_session, ctx_b, room_a_id)
    with pytest.raises(HTTPException):
        tenant_service.update_tenant(
            db_session, ctx_b, tenant_a_id, TenantUpdate(preferred_name="Hack")
        )
    with pytest.raises(HTTPException):
        room_service.create_room(
            db_session,
            ctx_b,
            RoomCreate(property_id=prop_a_id, label="X"),
        )

    apply_organisation_rls(db_session, org_a.id)
    db_session.expire_all()
    archived = tenant_service.archive_tenant(db_session, ctx_a, tenant_a_id)
    assert archived.status == RecordStatus.ARCHIVED
    archived_prop = property_service.archive_property(db_session, ctx_a, prop_a_id)
    assert archived_prop.status == RecordStatus.ARCHIVED
    with pytest.raises(HTTPException) as room_exc:
        room_service.create_room(
            db_session,
            ctx_a,
            RoomCreate(property_id=prop_a_id, label="Blocked"),
        )
    assert room_exc.value.status_code == 400

