"""Sensitive data redaction and metadata bounds for audit events."""

from __future__ import annotations

import json
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "apikey",
        "mfa",
        "otp",
        "session",
        "cookie",
        "client_secret",
    }
)

MAX_METADATA_BYTES = 4096
MAX_SUMMARY_LEN = 500
MAX_REASON_LEN = 1000
REDACTED = "[REDACTED]"


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEYS)


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (REDACTED if _is_sensitive_key(str(key)) else redact_value(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "…"
    return value


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if metadata is None:
        return None
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    cleaned = redact_value(metadata)
    encoded = json.dumps(cleaned, default=str)
    if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValueError(f"metadata exceeds {MAX_METADATA_BYTES} bytes after redaction")
    return cleaned


def sanitize_summary(summary: str | None) -> str | None:
    if summary is None:
        return None
    text = summary.strip()
    if len(text) > MAX_SUMMARY_LEN:
        return text[:MAX_SUMMARY_LEN] + "…"
    return text


def sanitize_reason(reason: str) -> str:
    text = reason.strip()
    if not text:
        raise ValueError("reason is required")
    if len(text) > MAX_REASON_LEN:
        raise ValueError(f"reason exceeds {MAX_REASON_LEN} characters")
    return text
