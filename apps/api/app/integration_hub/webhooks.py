"""Webhook signature verification and idempotent delivery records."""

from __future__ import annotations

import hashlib
import hmac


def payload_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def verify_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not secret:
        return False
    raw = signature.strip()
    if raw.startswith("sha256="):
        raw = raw[7:]
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, raw)
