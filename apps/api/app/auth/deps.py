"""FastAPI dependencies for Auth0 bearer authentication."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.auth.identity import resolve_user_from_claims
from app.auth.tokens import (
    TokenValidationError,
    http_401,
    http_403,
    token_has_mfa,
    validate_access_token,
)
from app.core.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_session


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise http_401("Missing Authorization header")
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        raise http_401("Authorization header must be Bearer <token>")
    return value.strip()


def get_token_claims(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    token = _bearer_token(authorization)
    try:
        return validate_access_token(token, settings)
    except TokenValidationError as exc:
        raise http_401(str(exc) or "Invalid or missing access token") from exc


def get_current_user(
    claims: dict[str, Any] = Depends(get_token_claims),
    session: Session = Depends(get_session),
) -> User:
    return resolve_user_from_claims(session, claims)


def require_mfa(
    claims: dict[str, Any] = Depends(get_token_claims),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Reject tokens that did not complete MFA when the API policy requires it."""
    enforce_mfa_policy(claims, settings)
    return claims


def enforce_mfa_policy(claims: dict[str, Any], settings: Settings) -> None:
    if settings.auth0_require_mfa_claim and not token_has_mfa(claims):
        raise http_403("Multi-factor authentication is required for this resource")


def get_staff_user(
    claims: dict[str, Any] = Depends(require_mfa),
    session: Session = Depends(get_session),
) -> User:
    """Authenticated user for staff paths after the MFA policy check."""
    return resolve_user_from_claims(session, claims)
