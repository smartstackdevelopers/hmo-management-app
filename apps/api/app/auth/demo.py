"""Local-only demo authentication for boss meetings (development + HMORE_DEMO_AUTH)."""

from __future__ import annotations

import time
import uuid
from typing import Any

import jwt
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.enums import HMoreRole
from app.ops.identity_bootstrap import grant_org_role, grant_super_admin
from app.rbac.roles import parse_role

DEMO_ISSUER = "https://hmore.local/demo/"
DEMO_TOKEN_TTL_SECONDS = 8 * 60 * 60

DEMO_ROLE_EMAILS: dict[str, str] = {
    HMoreRole.SUPER_ADMIN.value: "demo-super-admin@hmore.local",
    HMoreRole.ORGANISATION_ADMIN.value: "demo-org-admin@hmore.local",
    HMoreRole.LANDLORD.value: "demo-landlord@hmore.local",
    HMoreRole.TENANT.value: "demo-tenant@hmore.local",
    HMoreRole.SUPPORT_WORKER.value: "demo-support@hmore.local",
    HMoreRole.MAINTENANCE_CONTRACTOR.value: "demo-contractor@hmore.local",
}


def demo_auth_allowed(settings: Settings) -> bool:
    if not settings.hmore_demo_auth:
        return False
    env = (settings.environment or "").lower()
    return env in {"development", "dev", "local", "test"}


def demo_audience(settings: Settings) -> str:
    return settings.auth0_audience or "https://api.hmore.local"


def issue_demo_access_token(
    *,
    settings: Settings,
    subject: str,
    email: str,
    role: str,
) -> str:
    now = int(time.time())
    payload = {
        "sub": subject,
        "email": email,
        "email_verified": True,
        "iss": DEMO_ISSUER,
        "aud": demo_audience(settings),
        "iat": now,
        "exp": now + DEMO_TOKEN_TTL_SECONDS,
        "hmore_demo": True,
        "hmore_demo_role": role,
    }
    return jwt.encode(payload, settings.hmore_demo_auth_secret, algorithm="HS256")


def decode_demo_access_token(token: str, settings: Settings) -> dict[str, Any] | None:
    if not demo_auth_allowed(settings):
        return None
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "HS256":
            return None
        claims = jwt.decode(
            token,
            settings.hmore_demo_auth_secret,
            algorithms=["HS256"],
            audience=demo_audience(settings),
            issuer=DEMO_ISSUER,
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
    if not claims.get("hmore_demo"):
        return None
    if not claims.get("email"):
        return None
    return claims


def ensure_demo_user_for_role(session: Session, settings: Settings, role_value: str) -> dict[str, Any]:
    role = parse_role(role_value)
    email = DEMO_ROLE_EMAILS[role.value]
    display = f"Demo {role.value.replace('_', ' ').title()}"
    subject = f"demo|{role.value}|{uuid.uuid5(uuid.NAMESPACE_URL, email)}"

    if role == HMoreRole.SUPER_ADMIN:
        summary = grant_super_admin(session, email, display_name=display)
    else:
        summary = grant_org_role(
            session,
            email=email,
            role_value=role.value,
            organisation_slug=settings.hmore_demo_org_slug,
            organisation_name=settings.hmore_demo_org_name,
            display_name=display,
        )

    from app.db.models import User
    from sqlalchemy import select

    user = session.scalar(select(User).where(User.email == email))
    if user is not None:
        user.external_subject = subject
        user.display_name = display
        session.add(user)
        session.flush()

    token = issue_demo_access_token(
        settings=settings,
        subject=subject,
        email=email,
        role=role.value,
    )
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": DEMO_TOKEN_TTL_SECONDS,
        "role": role.value,
        "email": email,
        "user_id": summary.get("user_id"),
        "organisation_id": summary.get("organisation_id"),
        "demo": True,
        "warning": "Local demo auth only. Disabled unless HMORE_DEMO_AUTH=true and ENVIRONMENT=development.",
    }
