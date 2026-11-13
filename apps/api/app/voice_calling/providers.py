"""Telephony provider adapters — test mode only unless credentials approved."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass
class ProviderStatus:
    mode: str
    reachable: bool
    message: str


def provider_status(mode: str) -> ProviderStatus:
    if mode == "test":
        return ProviderStatus(mode="test", reachable=True, message="Mock telephony — no real call placed")
    if mode == "twilio":
        return ProviderStatus(
            mode="twilio",
            reachable=False,
            message="Twilio credentials required — PENDING APPROVAL",
        )
    return ProviderStatus(mode=mode, reachable=False, message="Provider not configured")


def start_mock_call(*, direction: str) -> str:
    return f"test-call-{uuid.uuid4().hex[:16]}"


def mock_speech_to_text(audio_payload: str | None) -> str:
    if not audio_payload:
        return ""
    if audio_payload.startswith("text:"):
        return audio_payload[5:500]
    return "I could not understand that."


def mock_text_to_speech(text: str) -> dict[str, str]:
    return {"format": "test", "payload_ref": f"tts-{hash(text) & 0xFFFFFF}"}
