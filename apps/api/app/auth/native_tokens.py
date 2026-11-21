"""Issue and decode native HMore access tokens (HS256)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from app.core.config import Settings

NATIVE_ISS = "https://hmore.local/native/"
NATIVE_CLAIM = "hmore_native"


def native_auth_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "hmore_native_auth", True))


def _secret(settings: Settings) -> str:
    secret = (getattr(settings, "hmore_native_auth_secret", None) or "").strip()
    if not secret:
        raise RuntimeError("HMORE_NATIVE_AUTH_SECRET is not configured")
    return secret


def native_subject_for_user(user_id: UUID) -> str:
    return f"hmore|{user_id}"


def issue_access_token(
    *,
    settings: Settings,
    user_id: UUID,
    email: str,
    authorization_version: int,
) -> tuple[str, int]:
    ttl = int(getattr(settings, "hmore_access_token_ttl_seconds", 900) or 900)
    now = datetime.now(UTC)
    payload = {
        "sub": native_subject_for_user(user_id),
        "email": email,
        "email_verified": True,
        "iss": NATIVE_ISS,
        "aud": getattr(settings, "hmore_native_audience", None)
        or settings.auth0_audience
        or "https://api.hmore.local",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        NATIVE_CLAIM: True,
        "authorization_version": authorization_version,
    }
    token = jwt.encode(payload, _secret(settings), algorithm="HS256")
    return token, ttl


def decode_native_access_token(token: str, settings: Settings) -> dict[str, Any] | None:
    if not native_auth_enabled(settings):
        return None
    try:
        claims = jwt.decode(
            token,
            _secret(settings),
            algorithms=["HS256"],
            audience=getattr(settings, "hmore_native_audience", None)
            or settings.auth0_audience
            or "https://api.hmore.local",
            issuer=NATIVE_ISS,
            options={
                "require": ["exp", "iss", "aud", "sub"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except jwt.PyJWTError:
        return None
    if claims.get(NATIVE_CLAIM) is not True:
        return None
    return claims


def new_refresh_token_value() -> str:
    return secrets.token_urlsafe(48)


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
