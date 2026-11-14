"""Break-glass identity bootstrap for local/staging (Auth0 users + HMore memberships).

First Auth0 login provisions a User row from the token. This module pre-creates users
by email and assigns one of the six approved roles before the user signs in.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.enums import HMoreRole, MembershipStatus
from app.rbac.assignment import bump_authorization_version
from app.rbac.roles import parse_role

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class BootstrapError(Exception):
    """Configuration or data error while bootstrapping."""


def assert_bootstrap_allowed(settings: Settings, *, token: str | None) -> None:
    if settings.is_development:
        return
    expected = (settings.hmore_bootstrap_token or "").strip()
    provided = (token or "").strip()
    if not expected:
        raise BootstrapError(
            "Bootstrap is disabled in non-development environments. "
            "Set HMORE_BOOTSTRAP_TOKEN and pass --token."
        )
    if provided != expected:
        raise BootstrapError("Invalid bootstrap token.")


def normalize_email(email: str) -> str:
    value = email.strip().lower()
    if "@" not in value:
        raise BootstrapError(f"Invalid email: {email}")
    return value


def get_or_create_user(session: Session, email: str, *, display_name: str | None = None) -> User:
    normalized = normalize_email(email)
    user = session.scalar(select(User).where(User.email == normalized))
    if user is not None:
        if display_name and display_name.strip() and user.display_name != display_name.strip():
            user.display_name = display_name.strip()
        return user
    user = User(
        email=normalized,
        display_name=(display_name.strip() if display_name and display_name.strip() else normalized),
        external_subject=None,
    )
    session.add(user)
    session.flush()
    return user


def get_or_create_organisation(session: Session, *, name: str, slug: str) -> Organisation:
    slug = slug.strip().lower()
    if not _SLUG_RE.match(slug):
        raise BootstrapError("Organisation slug must be lowercase letters, digits, and hyphens.")
    existing = session.scalar(select(Organisation).where(Organisation.slug == slug))
    if existing is not None:
        return existing
    org = Organisation(name=name.strip(), slug=slug)
    session.add(org)
    session.flush()
    return org


def upsert_membership(
    session: Session,
    *,
    user: User,
    role: HMoreRole,
    organisation_id: uuid.UUID | None,
) -> OrganisationMembership:
    if role == HMoreRole.SUPER_ADMIN:
        if organisation_id is not None:
            raise BootstrapError("Super Admin must not have organisation_id")
        existing = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.user_id == user.id,
                OrganisationMembership.role == HMoreRole.SUPER_ADMIN,
            )
        )
    else:
        if organisation_id is None:
            raise BootstrapError(f"{role.value} requires organisation_id")
        existing = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.user_id == user.id,
                OrganisationMembership.organisation_id == organisation_id,
            )
        )

    if existing is not None:
        existing.role = role
        existing.status = MembershipStatus.ACTIVE
        membership = existing
    else:
        membership = OrganisationMembership(
            user_id=user.id,
            organisation_id=organisation_id,
            role=role,
            status=MembershipStatus.ACTIVE,
        )
        session.add(membership)

    bump_authorization_version(session, user)
    session.flush()
    return membership


def grant_super_admin(session: Session, email: str, *, display_name: str | None = None) -> dict[str, Any]:
    user = get_or_create_user(session, email, display_name=display_name)
    membership = upsert_membership(session, user=user, role=HMoreRole.SUPER_ADMIN, organisation_id=None)
    return _summary(user, membership)


def grant_org_role(
    session: Session,
    *,
    email: str,
    role_value: str,
    organisation_slug: str,
    organisation_name: str | None = None,
    display_name: str | None = None,
) -> dict[str, Any]:
    role = parse_role(role_value)
    if role == HMoreRole.SUPER_ADMIN:
        raise BootstrapError("Use grant-super-admin for super_admin")
    org = get_or_create_organisation(
        session,
        name=organisation_name or organisation_slug.replace("-", " ").title(),
        slug=organisation_slug,
    )
    user = get_or_create_user(session, email, display_name=display_name)
    membership = upsert_membership(session, user=user, role=role, organisation_id=org.id)
    return {**_summary(user, membership), "organisation_slug": org.slug, "organisation_name": org.name}


def describe_user(session: Session, email: str) -> dict[str, Any]:
    normalized = normalize_email(email)
    user = session.scalar(select(User).where(User.email == normalized))
    if user is None:
        raise BootstrapError(f"No user found for {normalized}")
    memberships = session.scalars(
        select(OrganisationMembership).where(OrganisationMembership.user_id == user.id)
    ).all()
    return {
        "user_id": str(user.id),
        "email": user.email,
        "external_subject": user.external_subject,
        "display_name": user.display_name,
        "memberships": [
            {
                "role": m.role.value,
                "organisation_id": str(m.organisation_id) if m.organisation_id else None,
                "status": m.status.value,
            }
            for m in memberships
        ],
    }


def _summary(user: User, membership: OrganisationMembership) -> dict[str, Any]:
    return {
        "user_id": str(user.id),
        "email": user.email,
        "external_subject": user.external_subject,
        "role": membership.role.value,
        "organisation_id": str(membership.organisation_id) if membership.organisation_id else None,
        "status": membership.status.value,
    }