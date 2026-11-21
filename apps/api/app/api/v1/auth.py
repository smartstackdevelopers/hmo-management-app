from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.demo import DEMO_ROLE_EMAILS, demo_auth_allowed, ensure_demo_user_for_role
from app.auth.deps import get_current_user, get_staff_user, get_token_claims, require_mfa
from app.core.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])

DemoRole = Literal[
    "super_admin",
    "organisation_admin",
    "landlord",
    "tenant",
    "support_worker",
    "maintenance_contractor",
]


class DemoLoginBody(BaseModel):
    role: DemoRole = Field(description="One of the six approved HMore roles")


@router.post("/demo/login")
def demo_login(
    body: DemoLoginBody,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Issue a local demo Bearer token for boss meetings. Development only."""
    if not demo_auth_allowed(settings):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo auth is disabled. Set HMORE_DEMO_AUTH=true with ENVIRONMENT=development.",
        )
    if body.role not in DEMO_ROLE_EMAILS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role")
    return ensure_demo_user_for_role(session, settings, body.role)


@router.get("/demo/roles")
def demo_roles(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    if not demo_auth_allowed(settings):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo auth is disabled")
    return {
        "enabled": True,
        "roles": [
            {"role": role, "email": email} for role, email in DEMO_ROLE_EMAILS.items()
        ],
    }


@router.get("/me")
def read_me(
    user: User = Depends(get_current_user),
    claims: dict[str, Any] = Depends(get_token_claims),
) -> dict[str, Any]:
    """Return the authenticated HMore user mapped from the Auth0 subject.

    Interactive login success/failure is owned by Auth0. Backend security audits for
    invalid tokens, MFA policy denials, and permission denials are recorded in the
    auth dependency layer (see AUTH_TOKEN_INVALID / AUTH_MFA_REQUIRED /
    AUTH_ACCESS_DENIED).
    """
    return {
        "id": str(user.id),
        "external_subject": user.external_subject,
        "email": user.email,
        "display_name": user.display_name,
        "authorization_version": user.authorization_version,
        "token_sub": claims.get("sub"),
    }


@router.get("/staff-session")
def staff_session(
    user: User = Depends(get_staff_user),
    claims: dict[str, Any] = Depends(require_mfa),
) -> dict[str, Any]:
    """Staff/admin session probe. When AUTH0_REQUIRE_MFA_CLAIM is true, MFA is required.

    Role permissions are enforced via /api/v1/rbac (F1.4), not this probe.
    """
    return {
        "id": str(user.id),
        "external_subject": user.external_subject,
        "authorization_version": user.authorization_version,
        "mfa": "mfa" in (claims.get("amr") or []),
    }
