"""Validate Auth0-issued access tokens."""

from __future__ import annotations

from typing import Any

import jwt
from fastapi import HTTPException, status

from app.auth.jwks import get_jwks
from app.core.config import Settings


class TokenValidationError(Exception):
    """Raised when an access token fails verification."""


def _issuer(settings: Settings) -> str:
    if settings.auth0_issuer:
        return settings.auth0_issuer
    if not settings.auth0_domain:
        raise TokenValidationError("AUTH0_DOMAIN is not configured")
    return f"https://{settings.auth0_domain}/"


def validate_access_token(token: str, settings: Settings) -> dict[str, Any]:
    if not settings.auth0_domain or not settings.auth0_audience:
        raise TokenValidationError("Auth0 is not configured on the API")

    try:
        jwks = get_jwks(settings)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise TokenValidationError("Token header is missing kid")

        keys = jwks.get("keys") or []
        matching = next((key for key in keys if key.get("kid") == kid), None)
        if matching is None:
            jwks = get_jwks(settings, force_refresh=True)
            keys = jwks.get("keys") or []
            matching = next((key for key in keys if key.get("kid") == kid), None)
        if matching is None:
            raise TokenValidationError("Signing key not found in JWKS")

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(matching)
        claims = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=_issuer(settings),
            options={
                "require": ["exp", "iss", "aud", "sub"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except TokenValidationError:
        raise
    except jwt.PyJWTError as exc:
        raise TokenValidationError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — normalise provider/network failures
        raise TokenValidationError("Unable to validate access token") from exc

    if not claims.get("sub"):
        raise TokenValidationError("Token is missing sub")
    return claims


def token_has_mfa(claims: dict[str, Any]) -> bool:
    amr = claims.get("amr")
    if isinstance(amr, list):
        return "mfa" in amr
    return False


def http_401(detail: str = "Invalid or missing access token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def http_403(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
