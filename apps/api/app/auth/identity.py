"""Map verified Auth0 subjects onto HMore users.external_subject."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


def resolve_user_from_claims(session: Session, claims: dict[str, Any]) -> User:
    subject = claims.get("sub")
    if not subject or not isinstance(subject, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a stable subject",
        )

    existing = session.scalar(select(User).where(User.external_subject == subject))
    if existing is not None:
        display_name = _display_name(claims, fallback=existing.display_name)
        if display_name and display_name != existing.display_name:
            existing.display_name = display_name
        return existing

    email = claims.get("email")
    if not email or not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An email claim is required the first time a user signs in",
        )
    # Auth0 may omit email_verified on access tokens. Reject only an explicit false.
    if claims.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email must be verified before the account can be provisioned",
        )

    by_email = session.scalar(select(User).where(User.email == email))
    if by_email is not None:
        if by_email.external_subject and by_email.external_subject != subject:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already linked to a different identity",
            )
        by_email.external_subject = subject
        by_email.display_name = _display_name(claims, fallback=by_email.display_name)
        return by_email

    user = User(
        external_subject=subject,
        email=email,
        display_name=_display_name(claims, fallback=email),
    )
    session.add(user)
    session.flush()
    return user


def _display_name(claims: dict[str, Any], *, fallback: str) -> str:
    for key in ("name", "nickname"):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback
