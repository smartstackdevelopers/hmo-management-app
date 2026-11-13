"""F8.6 digital ID and e-signatures add-on tests."""

from __future__ import annotations

from pathlib import Path

from app.digital_id_esign.constants import ADDON_DISCLAIMER, DEFAULT_ESIGN_TEMPLATES, IDENTITY_DOCUMENT_CATEGORIES
from app.digital_id_esign.providers import sandbox_identity_check_create, verify_provider_webhook
from app.core.config import Settings
from app.rbac.matrix import permissions_for_role
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
import hashlib
import hmac
import json


def test_identity_categories_count() -> None:
    assert len(IDENTITY_DOCUMENT_CATEGORIES) == 4


def test_esign_templates_count() -> None:
    assert len(DEFAULT_ESIGN_TEMPLATES) == 7


def test_sandbox_identity_provider() -> None:
    result = sandbox_identity_check_create()
    assert result["mode"] == "sandbox"
    assert result["status"] == "pending"


def test_webhook_signature() -> None:
    settings = Settings(digital_id_esign_webhook_signing_secret="die-secret")
    body = json.dumps({"event_type": "test"}, sort_keys=True).encode()
    sig = hmac.new(b"die-secret", body, hashlib.sha256).hexdigest()
    verify_provider_webhook(body, sig, settings)


def test_disclaimer_distinguishes_advanced() -> None:
    assert "advanced" in ADDON_DISCLAIMER.lower() or "qualified" in ADDON_DISCLAIMER.lower()


def test_tenant_may_submit_identity() -> None:
    perms = permissions_for_role(HMoreRole.TENANT)
    assert Permission.DIGITAL_ID_ESIGN_IDENTITY_SUBMIT in perms
    assert Permission.DIGITAL_ID_ESIGN_SIGN in perms


def test_f86_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f86/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.6_DIGITAL_ID_ESIGN_FINAL_REPORT.md").is_file()


def test_alembic_head_f86() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["20261118_5400_f86"]
