"""F8.6 sandbox identity and e-sign provider adapters."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any

from app.core.config import Settings


def sandbox_identity_check_create() -> dict[str, Any]:
    return {
        "provider_ref": f"sandbox_id_{uuid.uuid4().hex[:12]}",
        "status": "pending",
        "mode": "sandbox",
    }


def sandbox_esign_envelope_create(title: str) -> dict[str, Any]:
    return {
        "provider_ref": f"sandbox_env_{uuid.uuid4().hex[:12]}",
        "status": "sent",
        "mode": "sandbox",
        "title": title,
    }


def verify_provider_webhook(body: bytes, signature: str | None, settings: Settings) -> None:
    secret = settings.digital_id_esign_webhook_signing_secret
    if not secret:
        raise ValueError("Webhook signing secret not configured")
    if not signature:
        raise ValueError("Missing webhook signature")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid webhook signature")
