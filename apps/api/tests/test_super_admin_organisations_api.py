"""Super Admin organisation list/create API (M10.1)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.db.models.organisation import Organisation
from app.db.models.user import User
from app.db.session import get_session
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.deps import get_authorization_context
from app.tenancy.deps import get_platform_context

pytestmark = pytest.mark.postgres


def _super_admin_ctx() -> AuthorizationContext:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        external_subject=f"auth0|{uuid.uuid4()}",
        email="super@example.com",
        display_name="Super",
        authorization_version=1,
    )
    membership = MembershipView(
        membership_id=uuid.uuid4(),
        role=HMoreRole.SUPER_ADMIN,
        organisation_id=None,
        status=MembershipStatus.ACTIVE,
    )
    return AuthorizationContext(
        user=user,  # type: ignore[arg-type]
        memberships=[membership],
        active_organisation_id=None,
        active_role=HMoreRole.SUPER_ADMIN,
    )


def _tenant_ctx(org_id: uuid.UUID) -> AuthorizationContext:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        external_subject=f"auth0|{uuid.uuid4()}",
        email="tenant@example.com",
        display_name="Tenant",
        authorization_version=1,
    )
    membership = MembershipView(
        membership_id=uuid.uuid4(),
        role=HMoreRole.TENANT,
        organisation_id=org_id,
        status=MembershipStatus.ACTIVE,
    )
    return AuthorizationContext(
        user=user,  # type: ignore[arg-type]
        memberships=[membership],
        active_organisation_id=org_id,
        active_role=HMoreRole.TENANT,
    )


@pytest.fixture
def governance_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLATFORM_GOVERNANCE_GLOBAL_ENABLED", "true")
    get_settings.cache_clear()


def test_platform_organisations_list_requires_super_admin(
    db_session,
    unique_suffix: str,
    governance_enabled: None,
) -> None:
    org = Organisation(
        id=uuid.uuid4(),
        name=f"Listed Org {unique_suffix}",
        slug=f"listed-{unique_suffix}",
        status=RecordStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.flush()

    sa_ctx = _super_admin_ctx()

    def override_session():
        try:
            yield db_session
        finally:
            pass

    def override_authz() -> AuthorizationContext:
        return sa_ctx

    def override_platform() -> AuthorizationContext:
        return sa_ctx

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_authorization_context] = override_authz
    app.dependency_overrides[get_platform_context] = override_platform
    client = TestClient(app)
    try:
        response = client.get("/api/v1/platform-governance/platform/organisations")
        assert response.status_code == 200
        payload = response.json()
        assert any(row["slug"] == f"listed-{unique_suffix}" for row in payload)
    finally:
        app.dependency_overrides.clear()

    tenant_ctx = _tenant_ctx(org.id)

    def override_tenant() -> AuthorizationContext:
        return tenant_ctx

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_authorization_context] = override_tenant
    client = TestClient(app)
    try:
        denied = client.get("/api/v1/platform-governance/platform/organisations")
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_create_organisation_super_admin(
    db_session,
    unique_suffix: str,
    governance_enabled: None,
) -> None:
    sa_ctx = _super_admin_ctx()
    db_session.add(
        User(
            id=sa_ctx.user.id,
            email=sa_ctx.user.email,
            external_subject=sa_ctx.user.external_subject,
            display_name=sa_ctx.user.display_name,
        )
    )
    db_session.flush()

    def override_session():
        try:
            yield db_session
        finally:
            pass

    def override_authz() -> AuthorizationContext:
        return sa_ctx

    def override_platform() -> AuthorizationContext:
        return sa_ctx

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_authorization_context] = override_authz
    app.dependency_overrides[get_platform_context] = override_platform
    client = TestClient(app)
    slug = f"created-{unique_suffix}"
    try:
        response = client.post(
            "/api/v1/organisations",
            json={"name": f"Created {unique_suffix}", "slug": slug},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["slug"] == slug
        persisted = db_session.get(Organisation, uuid.UUID(body["id"]))
        assert persisted is not None
        assert persisted.name == f"Created {unique_suffix}"
    finally:
        app.dependency_overrides.clear()