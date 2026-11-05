"""JWKS fetch and cache for Auth0 RS256 access-token verification."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import Settings

_jwks_cache: dict[str, Any] | None = None
_jwks_cached_at: float = 0.0
_JWKS_TTL_SECONDS = 3600


def clear_jwks_cache() -> None:
    global _jwks_cache, _jwks_cached_at
    _jwks_cache = None
    _jwks_cached_at = 0.0


def get_jwks(settings: Settings, *, force_refresh: bool = False) -> dict[str, Any]:
    global _jwks_cache, _jwks_cached_at
    if (
        not force_refresh
        and _jwks_cache is not None
        and (time.monotonic() - _jwks_cached_at) < _JWKS_TTL_SECONDS
    ):
        return _jwks_cache

    if not settings.auth0_domain:
        raise RuntimeError("AUTH0_DOMAIN is not configured")

    url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    with httpx.Client(timeout=10.0) as client:
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()

    _jwks_cache = payload
    _jwks_cached_at = time.monotonic()
    return payload


def set_jwks_for_tests(jwks: dict[str, Any]) -> None:
    """Inject a JWKS document for unit tests. Do not use in production paths."""
    global _jwks_cache, _jwks_cached_at
    _jwks_cache = jwks
    _jwks_cached_at = time.monotonic()
