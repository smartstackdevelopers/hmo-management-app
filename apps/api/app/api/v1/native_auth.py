"""Native HMore authentication HTTP API (Prompt 12)."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel, BeforeValidator, Field
from sqlalchemy.orm import Session

from app.auth import native_service
from app.auth.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.models import AccountStatus, User
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth-native"])


def _normalize_local_email(value: Any) -> str:
    """Accept normal emails plus local-dev ``*.local`` addresses (RFC 6762).

    Pydantic ``EmailStr`` / email-validator reject ``.local`` as special-use.
    HMore local demo accounts use ``@hmore.local`` and must remain usable
    without cloud/production email deliverability checks.
    """
    if not isinstance(value, str):
        raise TypeError("email must be a string")
    raw = value.strip()
    try:
        return validate_email(raw, check_deliverability=False).normalized
    except EmailNotValidError as exc:
        if "@" not in raw or raw.count("@") != 1:
            raise ValueError(str(exc)) from exc
        local_part, domain = raw.rsplit("@", 1)
        domain_l = domain.lower()
        if local_part and (domain_l.endswith(".local") or domain_l == "localhost"):
            return f"{local_part}@{domain_l}".lower()
        raise ValueError(str(exc)) from exc


LocalEmail = Annotated[str, BeforeValidator(_normalize_local_email)]


class RegisterBody(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: LocalEmail
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    requested_role: Literal["landlord", "tenant", "support_worker", "maintenance_contractor"]
    organisation_id: UUID | None = None
    organisation_slug: str | None = None
    invitation_code: str | None = None
    phone: str | None = None
    terms_accepted: bool
    privacy_accepted: bool


class LoginBody(BaseModel):
    email: LocalEmail
    password: str = Field(min_length=1, max_length=128)


class RefreshBody(BaseModel):
    refresh_token: str


class LogoutBody(BaseModel):
    refresh_token: str | None = None


class DecisionBody(BaseModel):
    rejection_reason: str | None = None


class CreateOrgAdminBody(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: LocalEmail
    password: str = Field(min_length=8, max_length=128)
    organisation_id: UUID


class AccountStatusBody(BaseModel):
    account_status: Literal["approved", "suspended", "disabled", "rejected", "pending"]


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordBody(BaseModel):
    email: LocalEmail


class ResetPasswordBody(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class BootstrapSuperAdminBody(BaseModel):
    email: LocalEmail
    password: str = Field(min_length=8, max_length=128)
    display_name: str = "Super Admin"


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return ua, ip


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterBody,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return native_service.register_user(
        session,
        settings,
        full_name=body.full_name,
        email=str(body.email),
        password=body.password,
        confirm_password=body.confirm_password,
        requested_role=body.requested_role,
        organisation_id=body.organisation_id,
        organisation_slug=body.organisation_slug,
        invitation_code=body.invitation_code,
        phone=body.phone,
        terms_accepted=body.terms_accepted,
        privacy_accepted=body.privacy_accepted,
    )


@router.post("/login")
def login(
    body: LoginBody,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    ua, ip = _client_meta(request)
    return native_service.login(
        session,
        settings,
        email=str(body.email),
        password=body.password,
        user_agent=ua,
        ip_address=ip,
    )


@router.post("/refresh")
def refresh(
    body: RefreshBody,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    ua, ip = _client_meta(request)
    return native_service.refresh_session(
        session,
        settings,
        refresh_token=body.refresh_token,
        user_agent=ua,
        ip_address=ip,
    )


@router.post("/logout")
def logout(
    body: LogoutBody,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return native_service.logout(session, refresh_token=body.refresh_token, user_id=None)


@router.get("/registration-requests")
def registration_requests(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return {"items": native_service.list_registration_requests(session, user)}


@router.post("/registration-requests/{request_id}/approve")
def approve_registration(
    request_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return native_service.decide_registration(session, actor=user, request_id=request_id, approve=True)


@router.post("/registration-requests/{request_id}/reject")
def reject_registration(
    request_id: UUID,
    body: DecisionBody,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return native_service.decide_registration(
        session,
        actor=user,
        request_id=request_id,
        approve=False,
        rejection_reason=body.rejection_reason,
    )


@router.post("/users/organisation-admin", status_code=status.HTTP_201_CREATED)
def create_org_admin(
    body: CreateOrgAdminBody,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return native_service.create_organisation_admin(
        session,
        actor=user,
        full_name=body.full_name,
        email=str(body.email),
        password=body.password,
        organisation_id=body.organisation_id,
    )


@router.patch("/users/{user_id}/account-status")
def patch_account_status(
    user_id: UUID,
    body: AccountStatusBody,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return native_service.set_account_status(
        session,
        actor=user,
        user_id=user_id,
        account_status=AccountStatus(body.account_status),
    )


@router.post("/password/change")
def password_change(
    body: ChangePasswordBody,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    return native_service.change_password(
        session,
        user=user,
        current_password=body.current_password,
        new_password=body.new_password,
    )


@router.post("/password/forgot")
def password_forgot(
    body: ForgotPasswordBody,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return native_service.request_password_reset(session, email=str(body.email))


@router.post("/password/reset")
def password_reset(
    body: ResetPasswordBody,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return native_service.reset_password(session, token=body.token, new_password=body.new_password)


@router.get("/notifications")
def notifications(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return native_service.list_notifications(session, user)


@router.post("/notifications/{notification_id}/read")
def notification_read(
    notification_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    return native_service.mark_notification_read(session, user, notification_id)


@router.post("/bootstrap-super-admin", status_code=status.HTTP_201_CREATED)
def bootstrap_super_admin(
    body: BootstrapSuperAdminBody,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    x_hmore_bootstrap: str | None = Header(default=None, alias="X-HMore-Bootstrap"),
) -> dict[str, Any]:
    """Create the first Super Admin locally. Disabled when a Super Admin already exists."""
    if settings.is_production:
        expected = (settings.hmore_bootstrap_token or "").strip()
        if not expected or x_hmore_bootstrap != expected:
            from fastapi import HTTPException

            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bootstrap forbidden")
    return native_service.ensure_bootstrap_super_admin(
        session,
        settings,
        email=str(body.email),
        password=body.password,
        display_name=body.display_name,
    )
