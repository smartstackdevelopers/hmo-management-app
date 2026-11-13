"""F8.1 AI voice calling add-on tests (mock telephony only)."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from app.ai_usage.features import FEATURE_VOICE_CALLING
from app.core.config import Settings
from app.voice_calling import assistant, providers
from app.voice_calling.service import verify_webhook_signature


def test_voice_feature_id_registered() -> None:
    assert FEATURE_VOICE_CALLING == "ai.addon.voice_calling"


def test_assistant_emergency_triggers_handover() -> None:
    text, handover, reason = assistant.generate_response("there is a fire emergency", language="en-GB")
    assert handover is True
    assert reason == "emergency_or_safety"
    assert "999" in text


def test_mock_provider_no_twilio_without_credentials() -> None:
    st = providers.provider_status("twilio")
    assert st.reachable is False


def test_webhook_signature_roundtrip() -> None:
    settings = Settings(voice_webhook_signing_secret="test-secret")
    body = json.dumps({"organisation_id": "00000000-0000-0000-0000-000000000001", "event": "incoming"}, sort_keys=True)
    sig = hmac.new(b"test-secret", body.encode(), hashlib.sha256).hexdigest()
    verify_webhook_signature(body.encode(), sig, settings)


def test_f81_docs_present() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docs/phase8/f81/ARCHITECTURE.md").is_file()
    assert (repo / "docs/phase8/F8.1_VOICE_CALLING_FINAL_REPORT.md").is_file()


def test_alembic_head_f81() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["20261113_4900_f81"]

