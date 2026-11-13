"""F8.9 deep integration hub add-on tests."""

from __future__ import annotations

import hmac
import hashlib
from pathlib import Path

from app.integration_hub.constants import ADDON_DISCLAIMER, HMORE_MODULE_KEYS, HUB_CATEGORIES
from app.integration_hub.webhooks import payload_hash, verify_signature
from app.rbac.matrix import permissions_for_role, role_has_permission
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission


def test_hub_categories_count() -> None:
    assert len(HUB_CATEGORIES) == 15


def test_hmore_module_keys() -> None:
    assert len(HMORE_MODULE_KEYS) == 12
    assert "ai_gateway" in HMORE_MODULE_KEYS


def test_disclaimer_requires_approval() -> None:
    assert "approval" in ADDON_DISCLAIMER.lower()


def test_webhook_signature_roundtrip() -> None:
    body = b'{"event":"test"}'
    secret = "test-signing-secret"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, f"sha256={sig}", secret)
    assert not verify_signature(body, "bad", secret)


def test_payload_hash_deterministic() -> None:
    assert payload_hash(b"x") == payload_hash(b"x")
    assert payload_hash(b"x") != payload_hash(b"y")


def test_org_admin_hub_permissions() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.INTEGRATION_HUB_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.INTEGRATION_HUB_WEBHOOKS)


def test_tenant_no_hub_manage() -> None:
    perms = permissions_for_role(HMoreRole.TENANT)
    assert Permission.INTEGRATION_HUB_MANAGE not in perms


def test_landlord_hub_read() -> None:
    perms = permissions_for_role(HMoreRole.LANDLORD)
    assert Permission.INTEGRATION_HUB_READ in perms


def test_f89_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f89/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.9_INTEGRATION_HUB_FINAL_REPORT.md").is_file()


def test_alembic_head_f89() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["20261122_5800_f811"]
