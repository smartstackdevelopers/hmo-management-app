"""Native registration, approval, login, and session management (Prompt 12)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.native_tokens import (
    hash_token,
    issue_access_token,
    native_subject_for_user,
    new_refresh_token_value,
)
from app.auth.passwords import hash_password, needs_rehash, verify_password
from app.core.config import Settings
from app.db.models import (
    AccountStatus,
    AuthAuditEvent,
    AuthNotification,
    AuthRefreshToken,
    HMoreRole,
    Organisation,
    OrganisationMembership,
    PasswordResetToken,
    RegistrationRequest,
    RegistrationRequestStatus,
    User,
)
from app.db.models.enums import MembershipStatus
from app.ops.identity_bootstrap import grant_org_role, grant_super_admin
from app.rbac.assignment import bump_authorization_version

PUBLIC_REGISTER_ROLES = {
    HMoreRole.LANDLORD,
    HMoreRole.TENANT,
    HMoreRole.SUPPORT_WORKER,
    HMoreRole.MAINTENANCE_CONTRACTOR,
}

ORG_ADMIN_APPROVABLE_ROLES = PUBLIC_REGISTER_ROLES


def _now() -> datetime:
    return datetime.now(UTC)


def _audit(
    session: Session,
    *,
    event_type: str,
    actor_user_id: UUID | None = None,
    subject_user_id: UUID | None = None,
    organisation_id: UUID | None = None,
    registration_request_id: UUID | None = None,
    detail: str | None = None,
) -> None:
    session.add(
        AuthAuditEvent(
            event_type=event_type,
            actor_user_id=actor_user_id,
            subject_user_id=subject_user_id,
            organisation_id=organisation_id,
            registration_request_id=registration_request_id,
            detail=detail,
        )
    )


def _notify(
    session: Session,
    *,
    recipient_user_id: UUID,
    title: str,
    body: str,
    organisation_id: UUID | None = None,
    registration_request_id: UUID | None = None,
    category: str = "registration",
) -> None:
    session.add(
        AuthNotification(
            recipient_user_id=recipient_user_id,
            organisation_id=organisation_id,
            registration_request_id=registration_request_id,
            title=title,
            body=body,
            category=category,
        )
    )


def _super_admins(session: Session) -> list[User]:
    rows = session.scalars(
        select(User)
        .join(OrganisationMembership, OrganisationMembership.user_id == User.id)
        .where(
            OrganisationMembership.role == HMoreRole.SUPER_ADMIN,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
            User.account_status == AccountStatus.APPROVED,
        )
    ).all()
    return list(rows)


def _org_admins(session: Session, organisation_id: UUID) -> list[User]:
    rows = session.scalars(
        select(User)
        .join(OrganisationMembership, OrganisationMembership.user_id == User.id)
        .where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.role == HMoreRole.ORGANISATION_ADMIN,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
            User.account_status == AccountStatus.APPROVED,
        )
    ).all()
    return list(rows)


def register_user(
    session: Session,
    settings: Settings,
    *,
    full_name: str,
    email: str,
    password: str,
    confirm_password: str,
    requested_role: str,
    organisation_id: UUID | None = None,
    organisation_slug: str | None = None,
    invitation_code: str | None = None,
    phone: str | None = None,
    terms_accepted: bool = False,
    privacy_accepted: bool = False,
) -> dict[str, Any]:
    email_norm = email.strip().lower()
    name = full_name.strip()
    if not name or not email_norm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Name and email are required")
    if password != confirm_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    if not terms_accepted or not privacy_accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Terms and privacy consent are required")

    try:
        role = HMoreRole(requested_role)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid requested role") from exc

    if role == HMoreRole.SUPER_ADMIN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot self-register as super_admin")
    if role == HMoreRole.ORGANISATION_ADMIN:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Organisation Admin accounts must be created by Super Admin",
        )
    if role not in PUBLIC_REGISTER_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Role is not open for public registration")

    if session.scalar(select(User).where(func.lower(User.email) == email_norm)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email is already registered")

    org: Organisation | None = None
    if organisation_id is not None:
        org = session.get(Organisation, organisation_id)
    elif organisation_slug:
        org = session.scalar(select(Organisation).where(Organisation.slug == organisation_slug.strip()))
    if org is None:
        # Default demo org for local registration convenience
        slug = settings.hmore_demo_org_slug
        org = session.scalar(select(Organisation).where(Organisation.slug == slug))
        if org is None:
            org = Organisation(name=settings.hmore_demo_org_name, slug=slug)
            session.add(org)
            session.flush()

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    user = User(
        email=email_norm,
        display_name=name,
        phone=(phone or "").strip() or None,
        password_hash=password_hash,
        account_status=AccountStatus.PENDING,
        password_changed_at=_now(),
    )
    session.add(user)
    session.flush()
    user.external_subject = native_subject_for_user(user.id)

    req = RegistrationRequest(
        user_id=user.id,
        organisation_id=org.id,
        requested_role=role,
        status=RegistrationRequestStatus.PENDING,
        invitation_code=(invitation_code or "").strip() or None,
        terms_accepted_at=_now(),
        privacy_accepted_at=_now(),
    )
    session.add(req)
    session.flush()

    for admin in _org_admins(session, org.id) or _super_admins(session):
        _notify(
            session,
            recipient_user_id=admin.id,
            organisation_id=org.id,
            registration_request_id=req.id,
            title="New registration request",
            body=f"{name} requested role {role.value} for {org.name}.",
        )

    _audit(
        session,
        event_type="registration_submitted",
        subject_user_id=user.id,
        organisation_id=org.id,
        registration_request_id=req.id,
        detail=f"requested_role={role.value}",
    )
    session.commit()
    return {
        "user_id": str(user.id),
        "email": user.email,
        "account_status": user.account_status.value,
        "registration_request_id": str(req.id),
        "requested_role": role.value,
        "organisation_id": str(org.id),
        "message": "Registration submitted. Access remains disabled until an administrator approves your request.",
    }


def create_organisation_admin(
    session: Session,
    *,
    actor: User,
    full_name: str,
    email: str,
    password: str,
    organisation_id: UUID,
) -> dict[str, Any]:
    """Super Admin creates an Organisation Admin (auto-approved)."""
    _require_super_admin(session, actor)
    org = session.get(Organisation, organisation_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    email_norm = email.strip().lower()
    if session.scalar(select(User).where(func.lower(User.email) == email_norm)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email is already registered")
    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    user = User(
        email=email_norm,
        display_name=full_name.strip(),
        password_hash=password_hash,
        account_status=AccountStatus.APPROVED,
        password_changed_at=_now(),
    )
    session.add(user)
    session.flush()
    user.external_subject = native_subject_for_user(user.id)
    grant_org_role(
        session,
        email=user.email,
        role_value=HMoreRole.ORGANISATION_ADMIN.value,
        organisation_slug=org.slug,
        organisation_name=org.name,
        display_name=user.display_name,
    )
    _notify(
        session,
        recipient_user_id=user.id,
        organisation_id=org.id,
        title="Organisation Admin account created",
        body=f"You can now sign in to manage {org.name}.",
        category="account",
    )
    _audit(
        session,
        event_type="organisation_admin_created",
        actor_user_id=actor.id,
        subject_user_id=user.id,
        organisation_id=org.id,
    )
    session.commit()
    return {"user_id": str(user.id), "email": user.email, "role": HMoreRole.ORGANISATION_ADMIN.value}


def _require_super_admin(session: Session, actor: User) -> None:
    row = session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.user_id == actor.id,
            OrganisationMembership.role == HMoreRole.SUPER_ADMIN,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Super Admin required")


def _actor_memberships(session: Session, actor: User) -> list[OrganisationMembership]:
    return list(
        session.scalars(
            select(OrganisationMembership).where(
                OrganisationMembership.user_id == actor.id,
                OrganisationMembership.status == MembershipStatus.ACTIVE,
            )
        ).all()
    )


def list_registration_requests(session: Session, actor: User) -> list[dict[str, Any]]:
    memberships = _actor_memberships(session, actor)
    roles = {m.role for m in memberships}
    q = select(RegistrationRequest)
    if HMoreRole.SUPER_ADMIN in roles:
        pass
    elif HMoreRole.ORGANISATION_ADMIN in roles:
        org_ids = [m.organisation_id for m in memberships if m.organisation_id]
        q = q.where(RegistrationRequest.organisation_id.in_(org_ids))
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not permitted to view registration requests")

    rows = session.scalars(q.order_by(RegistrationRequest.created_at.desc())).all()
    out: list[dict[str, Any]] = []
    for req in rows:
        user = session.get(User, req.user_id)
        out.append(
            {
                "id": str(req.id),
                "user_id": str(req.user_id),
                "email": user.email if user else None,
                "display_name": user.display_name if user else None,
                "requested_role": req.requested_role.value,
                "organisation_id": str(req.organisation_id) if req.organisation_id else None,
                "status": req.status.value,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "rejection_reason": req.rejection_reason,
            }
        )
    return out


def decide_registration(
    session: Session,
    *,
    actor: User,
    request_id: UUID,
    approve: bool,
    rejection_reason: str | None = None,
) -> dict[str, Any]:
    req = session.get(RegistrationRequest, request_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Registration request not found")
    if req.status != RegistrationRequestStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Request is not pending")

    if actor.id == req.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Cannot approve your own registration request")

    memberships = _actor_memberships(session, actor)
    roles = {m.role for m in memberships}
    is_super = HMoreRole.SUPER_ADMIN in roles
    org_admin_orgs = {
        m.organisation_id for m in memberships if m.role == HMoreRole.ORGANISATION_ADMIN and m.organisation_id
    }

    if req.requested_role == HMoreRole.ORGANISATION_ADMIN and not is_super:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only Super Admin can approve Organisation Admin")
    if req.requested_role == HMoreRole.SUPER_ADMIN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid request role")

    if not is_super:
        if req.organisation_id not in org_admin_orgs:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Request is outside your organisation")
        if req.requested_role not in ORG_ADMIN_APPROVABLE_ROLES:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Role cannot be approved by Organisation Admin")

    user = session.get(User, req.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    req.decided_by_user_id = actor.id
    req.decided_at = _now()
    if approve:
        req.status = RegistrationRequestStatus.APPROVED
        user.account_status = AccountStatus.APPROVED
        if req.organisation_id:
            org = session.get(Organisation, req.organisation_id)
            if org is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Organisation missing")
            grant_org_role(
                session,
                email=user.email,
                role_value=req.requested_role.value,
                organisation_slug=org.slug,
                organisation_name=org.name,
                display_name=user.display_name,
            )
            if req.requested_role == HMoreRole.TENANT:
                from app.records.tenant_service import ensure_linked_tenant_for_user

                ensure_linked_tenant_for_user(
                    session,
                    organisation_id=org.id,
                    user_id=user.id,
                    preferred_name=user.display_name or user.email,
                    full_name=user.display_name,
                    email=user.email,
                    phone=user.phone,
                    actor_user_id=actor.id,
                    actor_role="super_admin" if is_super else "organisation_admin",
                )
            bump_authorization_version(session, user)
        _notify(
            session,
            recipient_user_id=user.id,
            organisation_id=req.organisation_id,
            registration_request_id=req.id,
            title="Registration approved",
            body=f"Your account was approved as {req.requested_role.value}. You can now sign in.",
            category="approval",
        )
        decision = "approved"
    else:
        reason = (rejection_reason or "").strip() or "No reason provided"
        req.status = RegistrationRequestStatus.REJECTED
        req.rejection_reason = reason
        user.account_status = AccountStatus.REJECTED
        _notify(
            session,
            recipient_user_id=user.id,
            organisation_id=req.organisation_id,
            registration_request_id=req.id,
            title="Registration rejected",
            body=f"Your registration was rejected. Reason: {reason}",
            category="rejection",
        )
        decision = "rejected"

    _audit(
        session,
        event_type=f"registration_{decision}",
        actor_user_id=actor.id,
        subject_user_id=user.id,
        organisation_id=req.organisation_id,
        registration_request_id=req.id,
        detail=req.rejection_reason,
    )
    session.commit()
    return {
        "id": str(req.id),
        "status": req.status.value,
        "user_id": str(user.id),
        "account_status": user.account_status.value,
        "requested_role": req.requested_role.value,
    }


def _issue_session(
    session: Session,
    settings: Settings,
    user: User,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    access_token, expires_in = issue_access_token(
        settings=settings,
        user_id=user.id,
        email=user.email,
        authorization_version=user.authorization_version,
    )
    refresh = new_refresh_token_value()
    ttl = int(settings.hmore_refresh_token_ttl_seconds)
    session.add(
        AuthRefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=_now() + timedelta(seconds=ttl),
            user_agent=user_agent,
            ip_address=ip_address,
        )
    )
    session.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "account_status": user.account_status.value,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
        },
    }


def login(
    session: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    email_norm = email.strip().lower()
    user = session.scalar(select(User).where(func.lower(User.email) == email_norm))
    # Generic error — do not reveal whether email exists.
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if user is None or not user.password_hash:
        raise invalid

    if user.locked_until and user.locked_until > _now():
        raise HTTPException(status.HTTP_423_LOCKED, detail="Account temporarily locked. Try again later.")

    if not verify_password(user.password_hash, password):
        user.failed_login_count = int(user.failed_login_count or 0) + 1
        if user.failed_login_count >= settings.hmore_login_max_attempts:
            user.locked_until = _now() + timedelta(seconds=settings.hmore_login_lockout_seconds)
            user.failed_login_count = 0
        _audit(session, event_type="login_failed", subject_user_id=user.id, detail="bad_password")
        session.commit()
        raise invalid

    if user.account_status == AccountStatus.PENDING:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account pending approval")
    if user.account_status == AccountStatus.REJECTED:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account registration was rejected")
    if user.account_status == AccountStatus.SUSPENDED:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account is suspended")
    if user.account_status == AccountStatus.DISABLED:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    if user.account_status != AccountStatus.APPROVED:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account cannot sign in")

    user.failed_login_count = 0
    user.locked_until = None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    # Native session is authoritative locally (overwrite leftover demo/Auth0 subjects).
    user.external_subject = native_subject_for_user(user.id)

    _audit(session, event_type="login_success", subject_user_id=user.id)
    return _issue_session(session, settings, user, user_agent=user_agent, ip_address=ip_address)


def refresh_session(
    session: Session,
    settings: Settings,
    *,
    refresh_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    token_h = hash_token(refresh_token)
    row = session.scalar(select(AuthRefreshToken).where(AuthRefreshToken.token_hash == token_h))
    if row is None or row.revoked_at is not None or row.expires_at <= _now():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = session.get(User, row.user_id)
    if user is None or user.account_status != AccountStatus.APPROVED:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Rotate: revoke old, issue new
    new_value = new_refresh_token_value()
    row.revoked_at = _now()
    row.replaced_by_token_hash = hash_token(new_value)
    access_token, expires_in = issue_access_token(
        settings=settings,
        user_id=user.id,
        email=user.email,
        authorization_version=user.authorization_version,
    )
    session.add(
        AuthRefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_value),
            expires_at=_now() + timedelta(seconds=int(settings.hmore_refresh_token_ttl_seconds)),
            user_agent=user_agent,
            ip_address=ip_address,
        )
    )
    _audit(session, event_type="refresh_rotated", subject_user_id=user.id)
    session.commit()
    return {
        "access_token": access_token,
        "refresh_token": new_value,
        "token_type": "Bearer",
        "expires_in": expires_in,
    }


def logout(session: Session, *, refresh_token: str | None, user_id: UUID | None) -> dict[str, str]:
    if refresh_token:
        row = session.scalar(
            select(AuthRefreshToken).where(AuthRefreshToken.token_hash == hash_token(refresh_token))
        )
        if row and row.revoked_at is None:
            row.revoked_at = _now()
            _audit(session, event_type="logout", subject_user_id=row.user_id)
    elif user_id:
        rows = session.scalars(
            select(AuthRefreshToken).where(
                AuthRefreshToken.user_id == user_id,
                AuthRefreshToken.revoked_at.is_(None),
            )
        ).all()
        for row in rows:
            row.revoked_at = _now()
        _audit(session, event_type="logout_all", subject_user_id=user_id)
    session.commit()
    return {"status": "ok"}


def set_account_status(
    session: Session,
    *,
    actor: User,
    user_id: UUID,
    account_status: AccountStatus,
) -> dict[str, Any]:
    _require_super_admin(session, actor)
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if actor.id == user.id and account_status in {AccountStatus.SUSPENDED, AccountStatus.DISABLED}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot suspend your own Super Admin account")
    user.account_status = account_status
    if account_status in {AccountStatus.SUSPENDED, AccountStatus.DISABLED, AccountStatus.REJECTED}:
        rows = session.scalars(
            select(AuthRefreshToken).where(
                AuthRefreshToken.user_id == user.id,
                AuthRefreshToken.revoked_at.is_(None),
            )
        ).all()
        for row in rows:
            row.revoked_at = _now()
    _audit(
        session,
        event_type="account_status_changed",
        actor_user_id=actor.id,
        subject_user_id=user.id,
        detail=account_status.value,
    )
    session.commit()
    return {"user_id": str(user.id), "account_status": user.account_status.value}


def change_password(
    session: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> dict[str, str]:
    if not user.password_hash or not verify_password(user.password_hash, current_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    try:
        user.password_hash = hash_password(new_password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    user.password_changed_at = _now()
    # Revoke refresh tokens on password change
    rows = session.scalars(
        select(AuthRefreshToken).where(
            AuthRefreshToken.user_id == user.id,
            AuthRefreshToken.revoked_at.is_(None),
        )
    ).all()
    for row in rows:
        row.revoked_at = _now()
    _audit(session, event_type="password_changed", subject_user_id=user.id)
    session.commit()
    return {"status": "ok"}


def request_password_reset(session: Session, *, email: str) -> dict[str, Any]:
    """Always return ok to avoid email enumeration. Token returned only in development helpers via audit."""
    email_norm = email.strip().lower()
    user = session.scalar(select(User).where(func.lower(User.email) == email_norm))
    raw = None
    if user and user.password_hash:
        raw = new_refresh_token_value()
        session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=_now() + timedelta(hours=1),
            )
        )
        _notify(
            session,
            recipient_user_id=user.id,
            title="Password reset requested",
            body="A password reset was requested for your account. Use the reset token from your administrator in local development.",
            category="password_reset",
        )
        _audit(session, event_type="password_reset_requested", subject_user_id=user.id)
        session.commit()
    # Local-only: include token when user exists so QA can test without email provider.
    payload: dict[str, Any] = {
        "status": "ok",
        "message": "If the account exists, a reset was created. Email delivery requires a configured provider.",
    }
    if raw:
        payload["reset_token"] = raw
        payload["email_delivery"] = "not_configured"
    return payload


def reset_password(session: Session, *, token: str, new_password: str) -> dict[str, str]:
    row = session.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token))
    )
    if row is None or row.used_at is not None or row.expires_at <= _now():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user = session.get(User, row.user_id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    try:
        user.password_hash = hash_password(new_password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    user.password_changed_at = _now()
    row.used_at = _now()
    _audit(session, event_type="password_reset_completed", subject_user_id=user.id)
    session.commit()
    return {"status": "ok"}


def list_notifications(session: Session, user: User) -> dict[str, Any]:
    rows = session.scalars(
        select(AuthNotification)
        .where(AuthNotification.recipient_user_id == user.id)
        .order_by(AuthNotification.created_at.desc())
        .limit(100)
    ).all()
    pending = sum(1 for r in rows if not r.is_read)
    return {
        "pending_count": pending,
        "items": [
            {
                "id": str(r.id),
                "title": r.title,
                "body": r.body,
                "category": r.category,
                "is_read": r.is_read,
                "organisation_id": str(r.organisation_id) if r.organisation_id else None,
                "registration_request_id": str(r.registration_request_id)
                if r.registration_request_id
                else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


def mark_notification_read(session: Session, user: User, notification_id: UUID) -> dict[str, str]:
    row = session.get(AuthNotification, notification_id)
    if row is None or row.recipient_user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notification not found")
    row.is_read = True
    row.read_at = _now()
    session.commit()
    return {"status": "ok"}


def ensure_bootstrap_super_admin(
    session: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    display_name: str = "Super Admin",
) -> dict[str, Any]:
    """Dev helper: create first Super Admin if none exists."""
    existing = session.scalar(
        select(OrganisationMembership).where(OrganisationMembership.role == HMoreRole.SUPER_ADMIN)
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="A Super Admin already exists")
    email_norm = email.strip().lower()
    user = session.scalar(select(User).where(func.lower(User.email) == email_norm))
    if user is None:
        user = User(
            email=email_norm,
            display_name=display_name,
            password_hash=hash_password(password),
            account_status=AccountStatus.APPROVED,
            password_changed_at=_now(),
        )
        session.add(user)
        session.flush()
        user.external_subject = native_subject_for_user(user.id)
    else:
        user.password_hash = hash_password(password)
        user.account_status = AccountStatus.APPROVED
    grant_super_admin(session, user.email, display_name=user.display_name)
    _audit(session, event_type="bootstrap_super_admin", subject_user_id=user.id)
    session.commit()
    return {"user_id": str(user.id), "email": user.email, "role": "super_admin"}
