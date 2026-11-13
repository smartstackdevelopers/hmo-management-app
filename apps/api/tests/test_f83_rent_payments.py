"""F8.3 rent & tenancy payments add-on tests."""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from pathlib import Path

from app.core.config import Settings
from app.rent_payments.constants import ADDON_DISCLAIMER, PAYMENT_STATUSES
from app.rent_payments.providers import create_checkout_session, verify_webhook_signature


def test_payment_status_set_complete() -> None:
    assert len(PAYMENT_STATUSES) == 7


def test_checkout_test_mode() -> None:
    result = create_checkout_session(amount=Decimal("100.00"), currency="EUR", provider="test", settings=Settings())
    assert result.mode == "test"
    assert result.provider_session_id.startswith("test_cs_")


def test_webhook_signature() -> None:
    settings = Settings(rent_payment_webhook_signing_secret="rent-secret")
    body = json.dumps({"event": "test"}, sort_keys=True).encode()
    sig = hmac.new(b"rent-secret", body, hashlib.sha256).hexdigest()
    verify_webhook_signature(body, sig, settings)


def test_disclaimer_present() -> None:
    assert "test mode" in ADDON_DISCLAIMER.lower() or "manual" in ADDON_DISCLAIMER.lower()


def test_f83_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f83/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.3_RENT_PAYMENTS_FINAL_REPORT.md").is_file()


def test_alembic_head_f83() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["20261119_5500_f87"]
