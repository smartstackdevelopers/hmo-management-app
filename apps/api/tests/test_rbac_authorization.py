"""Authorization service and API gate tests. Uses mocked identity — not a live Auth0 tenant."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db.models.enums import HMoreRole, MembershipStatus
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.deps import get_authorization_context
from app.rbac.permissions import Permission
from app.rbac.service import (
    assert_assigned_support_caseload,
    assert_assigned_work_order,
    assert_landlord_property_access,
    assert_same_user,
    require_permission,
)


def _user(auth_version: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        external_subject=f"auth0|{uuid.uuid4()}",
        email=f"{uuid.uuid4().hex}@example.com",
        display_name="Test User",
        authorization_version=auth_version,
    )


def _ctx(
    role: HMoreRole,
    *,
    org_id: uuid.UUID | None = None,
    auth_version: int = 1,
) -> AuthorizationContext:
    user = _user(auth_version)
    organisation_id = None if role == HMoreRole.SUPER_ADMIN else (org_id or uuid.uuid4())
    membership = MembershipView(
        membership_id=uuid.uuid4(),
        role=role,
        organisation_id=organisation_id,
        status=MembershipStatus.ACTIVE,
    )
    return AuthorizationContext(
        user=user,  # type: ignore[arg-type]
        memberships=[membership],
        active_organisation_id=organisation_id,
        active_role=role,
    )


def test_require_permission_denies_missing() -> None:
    ctx = _ctx(HMoreRole.TENANT)
    with pytest.raises(HTTPException) as exc:
        require_permission(ctx, Permission.AUDIT_LOGS_READ)
    assert exc.value.status_code == 403


def test_require_permission_allows() -> None:
    ctx = _ctx(HMoreRole.SUPER_ADMIN)
    require_permission(ctx, Permission.ORGANISATIONS_MANAGE)


def test_tenant_own_profile_only() -> None:
    ctx = _ctx(HMoreRole.TENANT)
    assert_same_user(ctx, ctx.user.id)
    with pytest.raises(HTTPException) as exc:
        assert_same_user(ctx, uuid.uuid4())
    assert exc.value.status_code == 403


def test_landlord_cannot_access_unrelated_property() -> None:
    org = uuid.uuid4()
    ctx = _ctx(HMoreRole.LANDLORD, org_id=org)
    with pytest.raises(HTTPException) as exc:
        assert_landlord_property_access(
            ctx,
            property_organisation_id=org,
            landlord_user_id=uuid.uuid4(),
        )
    assert exc.value.status_code == 403


def test_contractor_cannot_access_unassigned_work_order() -> None:
    org = uuid.uuid4()
    ctx = _ctx(HMoreRole.MAINTENANCE_CONTRACTOR, org_id=org)
    with pytest.raises(HTTPException) as exc:
        assert_assigned_work_order(
            ctx,
            organisation_id=org,
            assignee_user_id=uuid.uuid4(),
        )
    assert exc.value.status_code == 403


def test_support_worker_cannot_access_unassigned_caseload() -> None:
    org = uuid.uuid4()
    ctx = _ctx(HMoreRole.SUPPORT_WORKER, org_id=org)
    with pytest.raises(HTTPException) as exc:
        assert_assigned_support_caseload(
            ctx,
            organisation_id=org,
            assigned_support_worker_id=uuid.uuid4(),
        )
    assert exc.value.status_code == 403


def test_org_admin_cannot_gain_super_admin_permission() -> None:
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN)
    assert not ctx.has_permission(Permission.ORGANISATIONS_CREATE)
    assert not ctx.has_permission(Permission.PLATFORM_SETTINGS_MANAGE)


def test_api_unauthenticated_returns_401() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/rbac/me")
    assert response.status_code == 401


def test_api_unauthorized_returns_403() -> None:
    ctx = _ctx(HMoreRole.TENANT)

    def _override() -> AuthorizationContext:
        return ctx

    app.dependency_overrides[get_authorization_context] = _override
    client = TestClient(app)
    try:
        response = client.get("/api/v1/rbac/gates/organisations.manage")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_api_authorized_returns_ok() -> None:
    ctx = _ctx(HMoreRole.SUPER_ADMIN)

    def _override() -> AuthorizationContext:
        return ctx

    app.dependency_overrides[get_authorization_context] = _override
    client = TestClient(app)
    try:
        response = client.get("/api/v1/rbac/gates/organisations.manage")
        assert response.status_code == 200
        assert response.json()["permission"] == Permission.ORGANISATIONS_MANAGE.value
    finally:
        app.dependency_overrides.clear()


def test_client_supplied_role_header_ignored_without_membership() -> None:
    """Headers alone must not invent permissions; deps reject unassigned roles."""
    from app.rbac.deps import _select_membership

    org = uuid.uuid4()
    memberships = [
        MembershipView(
            membership_id=uuid.uuid4(),
            role=HMoreRole.TENANT,
            organisation_id=org,
            status=MembershipStatus.ACTIVE,
        )
    ]
    with pytest.raises(HTTPException) as exc:
        _select_membership(memberships, org, HMoreRole.SUPER_ADMIN)
    assert exc.value.status_code == 403


def test_session_policy_exposes_authorization_version() -> None:
    ctx = _ctx(HMoreRole.LANDLORD, auth_version=4)
    from app.auth.session_policy import session_policy_payload

    payload = session_policy_payload(ctx)
    assert payload["authorization_version"] == 4
    assert payload["provider"] == "Auth0"
    assert "revocation" in payload
