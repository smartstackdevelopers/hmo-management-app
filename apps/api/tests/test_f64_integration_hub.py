"""F6.4 Integration Hub foundation tests."""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException
from sqlalchemy import select

from app.db.models.audit import AuditEvent
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.integrations import Integration, IntegrationSyncJob
from app.db.models.membership import OrganisationMembership
from app.db.models.organisation import Organisation
from app.db.models.user import User
from app.integrations import mapping as mapping_mod
from app.integrations import service as integration_service
from app.integrations import sync as integration_sync
from app.integrations.access import require_integrations_manage, require_integrations_read
from app.integrations.connectors.base import ConnectionTestResult
from app.integrations.connectors.rest import RestConnectorError, build_auth_headers, request_json
from app.integrations.crypto import decrypt_credentials, encrypt_credentials, public_credentials_view
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def _ctx(role: HMoreRole, organisation_id, user) -> OrganisationContext:
    return OrganisationContext(
        user=user,
        organisation_id=organisation_id,
        role=role,
        authorization=AuthorizationContext(
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
        ),
    )


def test_alembic_head_is_f64() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261111_4200_f64"]
    rev = script.get_revision("20261111_4200_f64")
    assert rev is not None
    assert rev.down_revision == "20261111_4100_f63"


def test_f64_permissions_matrix() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.INTEGRATIONS_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.INTEGRATIONS_READ)
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.INTEGRATIONS_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.INTEGRATIONS_MANAGE)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.INTEGRATIONS_MANAGE)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.INTEGRATIONS_READ)


def test_tenant_cannot_manage_integrations() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), user)
    with pytest.raises(Exception):
        require_integrations_manage(ctx)
    with pytest.raises(Exception):
        require_integrations_read(ctx)


def test_credential_encryption_roundtrip() -> None:
    ciphertext, meta = encrypt_credentials({"api_key": "super-secret-key", "ignored": "x"})
    assert ciphertext
    assert "api_key" in meta["keys_present"]
    assert "super-secret-key" not in ciphertext
    assert decrypt_credentials(ciphertext)["api_key"] == "super-secret-key"
    public = public_credentials_view(meta)
    assert public["configured"] is True
    assert "super-secret-key" not in str(public)


def test_oauth_auth_header_configuration() -> None:
    headers = build_auth_headers(
        "oauth2",
        {"bearer_token": "tok"},
        {"oauth_client_id": "client-1"},
    )
    assert headers["Authorization"] == "Bearer tok"
    assert headers["X-OAuth-Client-Id"] == "client-1"
    with pytest.raises(RestConnectorError):
        build_auth_headers("oauth2", {}, {"oauth_client_id": "client-1"})


def test_https_required_for_external_urls() -> None:
    with pytest.raises(RestConnectorError):
        request_json(method="GET", base_url="http://partner.example/api", path="/health", max_retries=0)


def test_connection_timeout_handling() -> None:
    import httpx

    with patch("app.integrations.connectors.rest.httpx.Client") as client_cls:
        client = MagicMock()
        client_cls.return_value.__enter__.return_value = client
        client.request.side_effect = httpx.TimeoutException("timeout")
        with patch("app.integrations.connectors.rest.time.sleep"):
            with pytest.raises(RestConnectorError) as exc:
                request_json(
                    method="GET",
                    base_url="https://partner.example/api",
                    path="/health",
                    auth_type="none",
                    max_retries=1,
                )
            assert "timed out" in str(exc.value).lower()


def test_rate_limit_retry_then_success() -> None:
    response_429 = MagicMock()
    response_429.status_code = 429
    response_429.headers = {"Retry-After": "0"}
    response_429.content = b""
    response_ok = MagicMock()
    response_ok.status_code = 200
    response_ok.content = b'{"ok":true}'
    response_ok.json.return_value = {"ok": True}
    with patch("app.integrations.connectors.rest.httpx.Client") as client_cls:
        client = MagicMock()
        client_cls.return_value.__enter__.return_value = client
        client.request.side_effect = [response_429, response_ok]
        with patch("app.integrations.connectors.rest.time.sleep"):
            status, body, _latency = request_json(
                method="GET",
                base_url="https://partner.example/api",
                path="/health",
                auth_type="none",
                max_retries=2,
            )
    assert status == 200
    assert body == {"ok": True}


def test_invalid_external_json_response() -> None:
    response = MagicMock()
    response.status_code = 200
    response.content = b"not-json"
    response.json.side_effect = ValueError("bad json")
    with patch("app.integrations.connectors.rest.httpx.Client") as client_cls:
        client = MagicMock()
        client_cls.return_value.__enter__.return_value = client
        client.request.return_value = response
        with pytest.raises(RestConnectorError) as exc:
            request_json(
                method="GET",
                base_url="https://partner.example/api",
                path="/health",
                auth_type="none",
                max_retries=0,
            )
        assert "Invalid JSON" in str(exc.value)


def test_mapping_validation_and_protected_fields() -> None:
    cleaned = mapping_mod.validate_mapping_entries(
        [{"source_field": "ext_name", "destination_field": "display_name", "data_type": "string", "required": True}]
    )
    assert cleaned[0]["source_field"] == "ext_name"
    with pytest.raises(HTTPException):
        mapping_mod.validate_mapping_entries(
            [{"source_field": "a", "destination_field": "b", "data_type": "not_a_type"}]
        )
    out, errors = mapping_mod.apply_mapping(
        {"ext_id": "x", "name": "Alice"},
        [
            {"source_field": "ext_id", "destination_field": "organisation_id", "data_type": "string"},
            {"source_field": "name", "destination_field": "display_name", "data_type": "string"},
        ],
    )
    assert "organisation_id" not in out
    assert out["display_name"] == "Alice"
    assert any("protected" in e.lower() for e in errors)


@pytest.mark.postgres
def test_integration_lifecycle_isolation_sync_and_audit(db_session, unique_suffix: str) -> None:
    org_a = Organisation(name="Org A", slug=f"org-a-{unique_suffix}")
    org_b = Organisation(name="Org B", slug=f"org-b-{unique_suffix}")
    user = User(
        email=f"f64-{unique_suffix}@example.com",
        display_name="F64 Admin",
        external_subject=f"auth0|f64-{unique_suffix}",
    )
    db_session.add_all([org_a, org_b, user])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            organisation_id=org_a.id,
            user_id=user.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, user)

    created = integration_service.create_integration(
        db_session,
        ctx,
        name="Council stub",
        provider_key="council_generic",
        api_base_url="https://partner.example/api",
        auth_type="api_key",
        credentials={"api_key": "live-secret-value"},
        config={"timeout_seconds": 5},
    )
    assert created["credentials"]["configured"] is True
    assert "live-secret-value" not in str(created)
    assert created["connection_status"] == "configured"

    row = db_session.get(Integration, uuid.UUID(created["id"]))
    assert row is not None
    assert row.credentials_encrypted
    assert "live-secret-value" not in row.credentials_encrypted
    assert decrypt_credentials(row.credentials_encrypted)["api_key"] == "live-secret-value"

    updated = integration_service.update_integration(
        db_session, ctx, row.id, name="Council stub renamed", description="Updated"
    )
    assert updated["name"] == "Council stub renamed"

    # Org isolation: other org context cannot see it
    other_user = User(
        email=f"f64b-{unique_suffix}@example.com",
        display_name="Other",
        external_subject=f"auth0|f64b-{unique_suffix}",
    )
    db_session.add(other_user)
    db_session.flush()
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, other_user)
    with pytest.raises(HTTPException) as not_found:
        integration_service.get_integration(db_session, ctx_b, row.id)
    assert not_found.value.status_code == 404

    # Mock successful connection test
    with patch(
        "app.integrations.service.get_adapter"
    ) as get_adapter:
        adapter = MagicMock()
        adapter.test_connection.return_value = ConnectionTestResult(
            ok=True, status="connected", detail="ok", http_status=200, latency_ms=12
        )
        get_adapter.return_value = adapter
        tested = integration_service.test_connection(db_session, ctx, row.id)
    assert tested["test"]["ok"] is True
    assert tested["integration"]["connection_status"] == "connected"

    mapping = integration_service.create_field_mapping(
        db_session,
        ctx,
        row.id,
        name="v1",
        mappings=[{"source_field": "ext", "destination_field": "label", "data_type": "string"}],
    )
    assert mapping["version"] == 1

    with patch("app.integrations.sync.get_adapter") as get_adapter_sync:
        adapter = MagicMock()
        adapter.health_sync.return_value = SimpleNamespace(
            success_count=1, failure_count=0, detail="synced", errors=[]
        )
        get_adapter_sync.return_value = adapter
        sync1 = integration_sync.start_sync(
            db_session, ctx, row.id, direction="health_check", idempotency_key="idem-1"
        )
        sync2 = integration_sync.start_sync(
            db_session, ctx, row.id, direction="health_check", idempotency_key="idem-1"
        )
    assert sync1["ok"] is True
    assert sync2.get("skipped") is True

    # Failed recovery path
    with patch("app.integrations.sync.get_adapter") as get_adapter_fail:
        adapter = MagicMock()
        adapter.health_sync.return_value = SimpleNamespace(
            success_count=0, failure_count=1, detail="upstream down", errors=["upstream down"]
        )
        get_adapter_fail.return_value = adapter
        failed = integration_sync.start_sync(
            db_session, ctx, row.id, direction="health_check", idempotency_key="idem-fail"
        )
    assert failed["ok"] is False
    assert failed["job"]["status"] == "failed"

    # Re-run recovery with success
    with patch("app.integrations.sync.get_adapter") as get_adapter_ok:
        adapter = MagicMock()
        adapter.health_sync.return_value = SimpleNamespace(
            success_count=1, failure_count=0, detail="recovered", errors=[]
        )
        get_adapter_ok.return_value = adapter
        recovered = integration_sync.start_sync(
            db_session, ctx, row.id, direction="health_check", idempotency_key="idem-recover"
        )
    assert recovered["ok"] is True

    # Disable
    disabled = integration_service.update_integration(db_session, ctx, row.id, is_enabled=False)
    assert disabled["is_enabled"] is False
    assert disabled["connection_status"] == "disabled"

    db_session.flush()
    actions = set(
        db_session.scalars(select(AuditEvent.action).where(AuditEvent.organisation_id == org_a.id)).all()
    )
    assert "integration.create" in actions
    assert "integration.update" in actions
    assert "integration.connection_test" in actions
    assert "integration.sync.start" in actions

    jobs = db_session.scalars(
        select(IntegrationSyncJob).where(IntegrationSyncJob.organisation_id == org_a.id)
    ).all()
    assert len(jobs) >= 3

    dash = integration_service.dashboard(db_session, ctx)
    assert dash["total_integrations"] >= 1
