"""Encrypt integration credentials at rest (Fernet). Never log plaintext secrets."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.secrets import redact_mapping

ALLOWED_SECRET_KEYS = frozenset(
    {"api_key", "bearer_token", "client_secret", "refresh_token", "username", "password"}
)


def _fernet() -> Fernet:
    settings = get_settings()
    raw = (settings.integration_secrets_key or "").strip()
    if raw:
        return Fernet(raw.encode("utf-8"))
    # Dev/test derivation — production should set INTEGRATION_SECRETS_KEY
    digest = hashlib.sha256(settings.integration_secrets_pepper.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_credentials(secrets: dict[str, Any] | None) -> tuple[str | None, dict[str, Any]]:
    """Return (ciphertext, public meta describing which keys are set)."""
    if not secrets:
        return None, {}
    cleaned: dict[str, str] = {}
    meta: dict[str, Any] = {"keys_present": []}
    for key, value in secrets.items():
        if key not in ALLOWED_SECRET_KEYS:
            continue
        if value is None or value == "":
            continue
        cleaned[key] = str(value)
        meta["keys_present"].append(key)
    if not cleaned:
        return None, {}
    token = _fernet().encrypt(json.dumps(cleaned, separators=(",", ":")).encode("utf-8"))
    return token.decode("utf-8"), meta


def decrypt_credentials(ciphertext: str | None) -> dict[str, str]:
    if not ciphertext:
        return {}
    try:
        raw = _fernet().decrypt(ciphertext.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items() if k in ALLOWED_SECRET_KEYS}
    except (InvalidToken, json.JSONDecodeError, ValueError):
        return {}


def public_credentials_view(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Safe response fragment — never includes secret values."""
    keys = list((meta or {}).get("keys_present") or [])
    return {
        "configured": bool(keys),
        "keys_present": keys,
        "values": redact_mapping({k: "***" for k in keys}),
    }
