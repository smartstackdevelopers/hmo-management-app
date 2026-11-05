"""Secret redaction helpers for logs and diagnostics. Never log raw credentials."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

REDACTED = "[REDACTED]"

_SENSITIVE_KEY_PARTS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "access_key",
        "secret_access",
        "api_key",
        "apikey",
        "authorization",
        "private_key",
        "client_secret",
        "refresh_token",
        "session",
        "cookie",
        "mfa",
        "otp",
    }
)

_BEARER_RE = re.compile(r"(Bearer\s+)(\S+)", re.IGNORECASE)


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def redact_mapping(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    result: dict[str, Any] = {}
    for key, value in data.items():
        if is_sensitive_key(str(key)):
            result[key] = REDACTED
        elif isinstance(value, dict):
            result[key] = redact_mapping(value)
        elif isinstance(value, str):
            result[key] = redact_text(value)
        else:
            result[key] = value
    return result


def redact_text(value: str) -> str:
    text = _BEARER_RE.sub(r"\1" + REDACTED, value)
    return text


def redact_database_url(url: str | None) -> str | None:
    """Strip credentials from a SQLAlchemy / libpq URL for safe logging."""
    if not url:
        return url
    parts = urlsplit(url)
    if parts.username or parts.password:
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
        netloc = host
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    return url
