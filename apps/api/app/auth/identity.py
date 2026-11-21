"""Map verified token subjects onto HMore users.external_subject."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.native_tokens import NATIVE_CLAIM
from app.db.models import AccountStatus, User


def _assert_account_may_access(user: User) -> None:
    status_value = getattr(user, "account_status", None)
    if status_value is None:
        return
    if status_value == AccountStatus.APPROVED:
        return
    if status_value == AccountStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account pending approval")
    if status_value == AccountStatus.REJECTED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account registration was rejected")
    if status_value == AccountStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is suspended")
    if status_value == AccountStatus.DISABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account cannot access the application")


def _resolve_native_user(session: Session, claims: dict[str, Any], subject: str) -> User | None:
    """Resolve native JWT subjects (``hmore|{user_id}``) without Auth0 provisioning."""
    if claims.get(NATIVE_CLAIM) is not True:
        return None
    if not subject.startswith("hmore|"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid native token subject",
        )
    try:
        user_id = UUID(subject.split("|", 1)[1])
    except (ValueError, IndexError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid native token subject",
        ) from exc

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Native login is authoritative locally — rebind if a prior demo/Auth0 subject remains.
    if user.external_subject != subject:
        user.external_subject = subject
    display_name = _display_name(claims, fallback=user.display_name)
    if display_name and display_name != user.display_name:
        user.display_name = display_name
    _assert_account_may_access(user)
    return user


def resolve_user_from_claims(session: Session, claims: dict[str, Any]) -> User:
    subject = claims.get("sub")
    if not subject or not isinstance(subject, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a stable subject",
        )

    native_user = _resolve_native_user(session, claims, subject)
    if native_user is not None:
        return native_user

    existing = session.scalar(select(User).where(User.external_subject == subject))
    if existing is not None:
        display_name = _display_name(claims, fallback=existing.display_name)
        if display_name and display_name != existing.display_name:
            existing.display_name = display_name
        _assert_account_may_access(existing)
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
        _assert_account_may_access(by_email)
        return by_email

    user = User(
        external_subject=subject,
        email=email,
        display_name=_display_name(claims, fallback=email),
        account_status=AccountStatus.APPROVED,
    )
    session.add(user)
    session.flush()
    _assert_account_may_access(user)
    return user


def _display_name(claims: dict[str, Any], *, fallback: str) -> str:
    for key in ("name", "nickname"):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback
