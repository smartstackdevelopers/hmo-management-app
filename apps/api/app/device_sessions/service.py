"""Register, list, revoke, and report lost device sessions.

Revoked and lost installation ids stay blocked. The client creates a new
installation id after the next full Auth0 login. Audit metadata records
installation and status only. It never records biometric data.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.auth.tokens import http_401
from app.db.models.device_sessions import MobileDeviceSession
from app.db.models.enums import HMoreRole
from app.device_sessions.guard import DEVICE_SESSION_REVOKED
from app.device_sessions.schemas import DeviceSessionRegister
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

_ADMIN_ROLES = {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}
_BLOCKED = {"revoked", "lost"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if value is None or not str(value).strip():
        return None
    try:
        return uuid.UUID(str(value).strip())
    except ValueError:
        return None


def own_sessions_statement(ctx: OrganisationContext) -> Any:
    return select(MobileDeviceSession).where(
        MobileDeviceSession.user_id == ctx.user_id,
        MobileDeviceSession.organisation_id == ctx.organisation_id,
    )


def session_out(row: MobileDeviceSession, *, current_id: uuid.UUID | None = None) -> dict[str, Any]:
    revoked_at = row.revoked_at
    last_seen = row.last_seen_at
    created_at = row.created_at
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "user_id": str(row.user_id),
        "installation_id": str(row.installation_id),
        "platform": row.platform,
        "device_name": row.device_name,
        "app_version": row.app_version,
        "status": row.status,
        "revoked_at": revoked_at.isoformat() if revoked_at is not None else None,
        "revoked_by_user_id": str(row.revoked_by_user_id) if row.revoked_by_user_id else None,
        "revocation_reason": row.revocation_reason,
        "last_seen_at": last_seen.isoformat() if last_seen is not None else None,
        "created_at": created_at.isoformat() if created_at is not None else None,
        "is_current": current_id is not None and row.id == current_id,
    }


def _audit(
    session: Session,
    ctx: OrganisationContext,
    *,
    action: str,
    row: MobileDeviceSession,
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
) -> None:
    record_event(
        session,
        action=action,
        resource_type="mobile_device_session",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=outcome,
        summary="Device session updated",
        metadata={
            "installation_id": str(row.installation_id),
            "platform": row.platform,
            "status": row.status,
            "revocation_reason": row.revocation_reason,
        },
    )


def register_session(session: Session, ctx: OrganisationContext, body: DeviceSessionRegister) -> dict[str, Any]:
    """Create or refresh an active installation.

    A revoked or lost installation returns 403 ``session_revoked`` and stays
    in that status. The same installation id is not reactivated.
    """
    apply_platform_rls_bypass(session)
    try:
        existing = session.scalar(
            select(MobileDeviceSession).where(
                MobileDeviceSession.user_id == ctx.user_id,
                MobileDeviceSession.installation_id == body.installation_id,
            )
        )
        if existing is not None and existing.status in _BLOCKED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="session_revoked")
        if existing is not None:
            existing.organisation_id = ctx.organisation_id
            existing.platform = body.platform
            existing.device_name = body.device_name
            existing.app_version = body.app_version
            existing.status = "active"
            existing.last_seen_at = _now()
            session.flush()
            _audit(session, ctx, action=audit_events.DEVICE_SESSION_REGISTERED, row=existing)
            return session_out(existing, current_id=existing.id)

        row = MobileDeviceSession(
            id=uuid.uuid4(),
            organisation_id=ctx.organisation_id,
            user_id=ctx.user_id,
            installation_id=body.installation_id,
            platform=body.platform,
            device_name=body.device_name,
            app_version=body.app_version,
            status="active",
            last_seen_at=_now(),
        )
        session.add(row)
        session.flush()
        _audit(session, ctx, action=audit_events.DEVICE_SESSION_REGISTERED, row=row)
        return session_out(row, current_id=row.id)
    finally:
        apply_organisation_rls(session, ctx.organisation_id)


def list_own_sessions(
    session: Session,
    ctx: OrganisationContext,
    current_header: str | None = None,
) -> list[dict[str, Any]]:
    current_id = _parse_uuid(current_header)
    rows = list(session.scalars(own_sessions_statement(ctx)).all())
    visible = [
        row
        for row in rows
        if row.user_id == ctx.user_id and row.organisation_id == ctx.organisation_id
    ]
    return [session_out(row, current_id=current_id) for row in visible]


def _load_for_actor(session: Session, ctx: OrganisationContext, session_id: uuid.UUID) -> MobileDeviceSession:
    row = session.get(MobileDeviceSession, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device session not found")
    if row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device session is in another organisation")
    if row.user_id == ctx.user_id:
        return row
    if ctx.role in _ADMIN_ROLES:
        return row
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device session belongs to another user")


def get_session(
    session: Session,
    ctx: OrganisationContext,
    session_id: uuid.UUID,
    current_header: str | None = None,
) -> dict[str, Any]:
    row = _load_for_actor(session, ctx, session_id)
    return session_out(row, current_id=_parse_uuid(current_header))


def _mark(
    session: Session,
    ctx: OrganisationContext,
    session_id: uuid.UUID,
    *,
    status_value: str,
    reason: str | None,
    action: str,
) -> dict[str, Any]:
    row = _load_for_actor(session, ctx, session_id)
    changed = row.status != status_value
    row.status = status_value
    if row.revoked_at is None:
        row.revoked_at = _now()
    row.revoked_by_user_id = ctx.user_id
    if reason:
        row.revocation_reason = reason
    row.updated_at = _now()
    session.flush()
    if changed:
        _audit(session, ctx, action=action, row=row)
    return session_out(row, current_id=row.id if row.user_id == ctx.user_id else None)


def revoke_session(
    session: Session,
    ctx: OrganisationContext,
    session_id: uuid.UUID,
    reason: str | None,
) -> dict[str, Any]:
    return _mark(
        session,
        ctx,
        session_id,
        status_value="revoked",
        reason=reason,
        action=audit_events.DEVICE_SESSION_REVOKED,
    )


def report_lost(
    session: Session,
    ctx: OrganisationContext,
    session_id: uuid.UUID,
    reason: str | None,
) -> dict[str, Any]:
    return _mark(
        session,
        ctx,
        session_id,
        status_value="lost",
        reason=reason or "reported_lost",
        action=audit_events.DEVICE_SESSION_LOST,
    )


def get_current_session(session: Session, ctx: OrganisationContext, header: str | None) -> dict[str, Any]:
    """Return the caller's session, including revoked and lost rows.

    This route is the status check. Other routes reject those statuses with 401
    before the handler runs. An unknown id or another user's id is 401
    ``device_session_revoked`` so the client clears its local tokens.
    """
    session_id = _parse_uuid(header)
    if session_id is None:
        raise http_401(DEVICE_SESSION_REVOKED)
    apply_platform_rls_bypass(session)
    try:
        row = session.get(MobileDeviceSession, session_id)
    finally:
        apply_organisation_rls(session, ctx.organisation_id)
    if row is None or row.user_id != ctx.user_id:
        raise http_401(DEVICE_SESSION_REVOKED)
    return session_out(row, current_id=row.id)
