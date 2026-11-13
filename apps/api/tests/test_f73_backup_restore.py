"""F7.3 backup and restore drill tests."""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.backup import access as backup_access
from app.backup.integrity import sha256_file
from app.backup import service as backup_service
from app.core.config import get_settings
from app.db.models.enums import HMoreRole, MembershipStatus
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def _ctx(role: HMoreRole, organisation_id: uuid.UUID) -> OrganisationContext:
    user = SimpleNamespace(id=uuid.uuid4())
    authz = AuthorizationContext(
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
    return OrganisationContext(user=user, organisation_id=organisation_id, role=role, authorization=authz)


def test_alembic_f73_revision_chain() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    rev = script.get_revision("20261112_4700_f73")
    assert rev is not None
    assert rev.down_revision == "20261112_4600_f72"


def test_backup_permissions_super_admin_only() -> None:
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.BACKUP_MANAGE)
    assert not role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.BACKUP_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.BACKUP_READ)


def test_org_admin_denied_backup_manage() -> None:
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, uuid.uuid4())
    with pytest.raises(Exception):
        backup_access.require_backup_manage(ctx)


def test_idempotency_prevents_duplicate_completed_backup() -> None:
    key = backup_service._idempotency_key("config_manifest", "daily")  # noqa: SLF001
    assert "config_manifest" in key


@pytest.mark.postgres
def test_config_manifest_backup_and_drill(db_session, unique_suffix: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.db.models.organisation import Organisation
    from app.db.models.user import User

    monkeypatch.setenv("BACKUP_ENABLED", "true")
    monkeypatch.setenv("BACKUP_RESTORE_DRILL_ALLOWED", "true")
    get_settings.cache_clear()

    org = Organisation(name=f"Bk-{unique_suffix}", slug=f"bk-{unique_suffix}")
    admin = User(
        email=f"bk-{unique_suffix}@example.com",
        display_name="Backup Admin",
        external_subject=f"auth0|bk-{unique_suffix}",
    )
    db_session.add_all([org, admin])
    db_session.flush()
    ctx = OrganisationContext(
        user=admin,
        organisation_id=org.id,
        role=HMoreRole.SUPER_ADMIN,
        authorization=_ctx(HMoreRole.SUPER_ADMIN, org.id).authorization,
    )

    result = backup_service.start_backup(session=db_session, ctx=ctx, backup_type="config_manifest", force=True)
    backup = result["backup"]
    assert backup["status"] == "verified"
    assert backup["checksum_sha256"]

    drill = backup_service.run_restore_drill(db_session, ctx, uuid.UUID(backup["id"]))
    assert drill["status"] == "passed"

