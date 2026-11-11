"""F4.6 device sessions: register, list own, revoke, cross-org denial, lost, header block.

No database is required. Auth0 Management API credentials are not used.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException
from pydantic import ValidationError

from app.audit.events import DEVICE_SESSION_LOST, DEVICE_SESSION_REGISTERED, DEVICE_SESSION_REVOKED
from app.core.config import Settings
from app.db.models.audit import AuditEvent
from app.db.models.device_sessions import MobileDeviceSession
from app.db.models.enums import HMoreRole, MembershipStatus
from app.device_sessions.auth0_management import management_api_revocation
from app.device_sessions.guard import DEVICE_SESSION_REVOKED as REVOKED_DETAIL
from app.device_sessions.guard import enforce_device_session
from app.device_sessions.schemas import DeviceSessionRegister
from app.device_sessions.service import (
    get_current_session,
    list_own_sessions,
    own_sessions_statement,
    register_session,
    report_lost,
    revoke_session,
)
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext


def _ctx(
    role: HMoreRole = HMoreRole.TENANT,
    org_id: uuid.UUID | None = None,
) -> OrganisationContext:
    organisation_id = org_id or uuid.uuid4()
    user_id = uuid.uuid4()
    user = SimpleNamespace(
        id=user_id,
        authorization_version=1,
        external_subject="auth0|device",
        email="device@example.com",
        display_name="Device",
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


def _row(
    ctx: OrganisationContext,
    *,
    status: str = "active",
    user_id: uuid.UUID | None = None,
    organisation_id: uuid.UUID | None = None,
) -> MobileDeviceSession:
    return MobileDeviceSession(
        id=uuid.uuid4(),
        organisation_id=organisation_id or ctx.organisation_id,
        user_id=user_id or ctx.user_id,
        installation_id=uuid.uuid4(),
        platform="ios",
        device_name="Phone",
        app_version="1.0.0",
        status=status,
        last_seen_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )


def _added(session: MagicMock) -> list[object]:
    return [call.args[0] for call in session.add.call_args_list if call.args]


def test_alembic_head_is_f46_device_sessions() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261110_3500_f52"]
    f46 = script.get_revision("20261110_3300_f46")
    assert f46 is not None
    assert f46.down_revision == "20261110_3200_f45"
    f45 = script.get_revision("20261110_3200_f45")
    assert f45 is not None
    assert f45.down_revision == "20261110_3000_f43"


def test_register_creates_active_session_without_biometric_data() -> None:
    ctx = _ctx()
    session = MagicMock()
    session.scalar.return_value = None
    installation_id = uuid.uuid4()
    body = DeviceSessionRegister(installation_id=installation_id, platform="android", device_name="Pixel", app_version="1.4.0")
    out = register_session(session, ctx, body)
    rows = _added(session)
    device = next(row for row in rows if isinstance(row, MobileDeviceSession))
    audit = next(row for row in rows if isinstance(row, AuditEvent))
    assert device.user_id == ctx.user_id
    assert device.organisation_id == ctx.organisation_id
    assert device.installation_id == installation_id
    assert device.status == "active"
    assert out["id"] == str(device.id)
    assert out["status"] == "active"
    assert audit.action == DEVICE_SESSION_REGISTERED
    assert set(audit.metadata_json or {}) <= {
        "installation_id",
        "platform",
        "status",
        "revocation_reason",
    }
    blob = json.dumps(audit.metadata_json).lower()
    for word in ("fingerprint", "biometric", "face_template", "token"):
        assert word not in blob


def test_register_rejects_biometric_fields() -> None:
    with pytest.raises(ValidationError):
        DeviceSessionRegister.model_validate(
            {
                "installation_id": str(uuid.uuid4()),
                "platform": "ios",
                "fingerprint": "template",
            }
        )


def test_revoked_installation_cannot_be_reactivated() -> None:
    ctx = _ctx()
    existing = _row(ctx, status="revoked")
    session = MagicMock()
    session.scalar.return_value = existing
    body = DeviceSessionRegister(installation_id=existing.installation_id, platform="ios")
    with pytest.raises(HTTPException) as exc:
        register_session(session, ctx, body)
    assert exc.value.status_code == 403
    assert exc.value.detail == "session_revoked"
    assert existing.status == "revoked"
    assert not any(isinstance(row, MobileDeviceSession) for row in _added(session))


def test_active_register_updates_the_same_installation() -> None:
    ctx = _ctx()
    existing = _row(ctx, status="active")
    session = MagicMock()
    session.scalar.return_value = existing
    body = DeviceSessionRegister(
        installation_id=existing.installation_id,
        platform="android",
        app_version="2.0.0",
    )
    out = register_session(session, ctx, body)
    assert existing.platform == "android"
    assert existing.app_version == "2.0.0"
    assert existing.status == "active"
    assert out["id"] == str(existing.id)
    assert not any(isinstance(row, MobileDeviceSession) for row in _added(session))


def test_list_own_sessions_drops_other_users() -> None:
    ctx = _ctx()
    own = _row(ctx)
    other = _row(ctx, user_id=uuid.uuid4())
    session = MagicMock()
    session.scalars.return_value.all.return_value = [own, other]
    items = list_own_sessions(session, ctx)
    assert [item["id"] for item in items] == [str(own.id)]
    sql = str(own_sessions_statement(ctx))
    assert "mobile_device_sessions.user_id" in sql
    assert "mobile_device_sessions.organisation_id" in sql


def test_owner_can_revoke_own_session() -> None:
    ctx = _ctx()
    row = _row(ctx)
    session = MagicMock()
    session.get.return_value = row
    out = revoke_session(session, ctx, row.id, "user_sign_out")
    assert row.status == "revoked"
    assert row.revoked_by_user_id == ctx.user_id
    assert row.revoked_at is not None
    assert row.revocation_reason == "user_sign_out"
    assert out["status"] == "revoked"
    audit = next(item for item in _added(session) if isinstance(item, AuditEvent))
    assert audit.action == DEVICE_SESSION_REVOKED


def test_org_admin_can_revoke_another_user_in_the_same_org() -> None:
    ctx = _ctx(role=HMoreRole.ORGANISATION_ADMIN)
    row = _row(ctx, user_id=uuid.uuid4())
    session = MagicMock()
    session.get.return_value = row
    out = revoke_session(session, ctx, row.id, "admin_sign_out")
    assert row.status == "revoked"
    assert row.revoked_by_user_id == ctx.user_id
    assert out["status"] == "revoked"


def test_support_worker_cannot_revoke_another_users_session() -> None:
    ctx = _ctx(role=HMoreRole.SUPPORT_WORKER)
    row = _row(ctx, user_id=uuid.uuid4())
    session = MagicMock()
    session.get.return_value = row
    with pytest.raises(HTTPException) as exc:
        revoke_session(session, ctx, row.id, None)
    assert exc.value.status_code == 403
    assert row.status == "active"


def test_deny_cross_org_revoke() -> None:
    ctx = _ctx(role=HMoreRole.ORGANISATION_ADMIN)
    row = _row(ctx, organisation_id=uuid.uuid4())
    session = MagicMock()
    session.get.return_value = row
    with pytest.raises(HTTPException) as exc:
        revoke_session(session, ctx, row.id, "no")
    assert exc.value.status_code == 403
    assert row.status == "active"
    assert row.revoked_at is None


def test_absent_device_session_header_is_allowed() -> None:
    session = MagicMock()
    assert enforce_device_session(session, uuid.uuid4(), None) is None
    assert enforce_device_session(session, uuid.uuid4(), "  ") is None
    session.get.assert_not_called()


def test_revoked_header_is_blocked() -> None:
    ctx = _ctx()
    row = _row(ctx, status="revoked")
    seen = row.last_seen_at
    session = MagicMock()
    session.get.return_value = row
    with pytest.raises(HTTPException) as exc:
        enforce_device_session(session, ctx.user_id, str(row.id))
    assert exc.value.status_code == 401
    assert exc.value.detail == REVOKED_DETAIL
    assert row.last_seen_at == seen


def test_wrong_user_header_is_blocked() -> None:
    ctx = _ctx()
    row = _row(ctx, user_id=uuid.uuid4())
    session = MagicMock()
    session.get.return_value = row
    with pytest.raises(HTTPException) as exc:
        enforce_device_session(session, ctx.user_id, str(row.id))
    assert exc.value.status_code == 401
    assert exc.value.detail == REVOKED_DETAIL


def test_lost_workflow_blocks_later_calls() -> None:
    ctx = _ctx()
    row = _row(ctx, status="active")
    session = MagicMock()
    session.get.return_value = row
    out = report_lost(session, ctx, row.id, "phone missing")
    assert row.status == "lost"
    assert row.revoked_at is not None
    assert row.revoked_by_user_id == ctx.user_id
    assert row.revocation_reason == "phone missing"
    assert out["status"] == "lost"
    audit = next(item for item in _added(session) if isinstance(item, AuditEvent))
    assert audit.action == DEVICE_SESSION_LOST
    seen = row.last_seen_at
    with pytest.raises(HTTPException) as exc:
        enforce_device_session(session, ctx.user_id, str(row.id))
    assert exc.value.status_code == 401
    assert exc.value.detail == REVOKED_DETAIL
    assert row.last_seen_at == seen
    current = get_current_session(session, ctx, str(row.id))
    assert current["status"] == "lost"


def test_active_header_updates_last_seen() -> None:
    ctx = _ctx()
    row = _row(ctx, status="active")
    previous = row.last_seen_at
    session = MagicMock()
    session.get.return_value = row
    found = enforce_device_session(session, ctx.user_id, str(row.id))
    assert found is row
    assert row.last_seen_at > previous


def test_auth0_management_api_is_not_called() -> None:
    configured = Settings(
        auth0_mgmt_domain="tenant.eu.auth0.com",
        auth0_mgmt_client_id="mgmt-id",
        auth0_mgmt_client_secret="mgmt-secret",
    )
    assert management_api_revocation(configured) == {"configured": True, "called": False}
    assert management_api_revocation(Settings()) == {"configured": False, "called": False}
