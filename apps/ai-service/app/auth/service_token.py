from __future__ import annotations

import hmac
import secrets

from app.core.config import Settings
from app.core.errors import AuthError


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def verify_service_token(settings: Settings, authorization: str | None) -> None:
    """Require a configured shared secret bearer token for protected AI routes."""
    if not settings.service_auth_configured:
        raise AuthError("AI service authentication is not configured")
    presented = extract_bearer_token(authorization)
    if not presented:
        raise AuthError("Missing or invalid Authorization bearer token")
    expected = settings.ai_service_token.encode("utf-8")
    given = presented.encode("utf-8")
    if not hmac.compare_digest(expected, given):
        # Constant-time compare fails on length mismatch — still deny without leaking.
        secrets.compare_digest(b"x" * 32, b"y" * 32)
        raise AuthError("Invalid service token")
