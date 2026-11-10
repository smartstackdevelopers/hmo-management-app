"""Register and list the caller's own Expo push tokens."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.push_devices import PushDeviceToken
from app.push.schemas import PushDeviceRegister
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _find_token(session: Session, expo_push_token: str) -> PushDeviceToken | None:
    return session.scalar(select(PushDeviceToken).where(PushDeviceToken.expo_push_token == expo_push_token))


def _owns(row: PushDeviceToken, ctx: OrganisationContext) -> bool:
    return row.organisation_id == ctx.organisation_id and row.user_id == ctx.user_id


def _device_out(row: PushDeviceToken) -> dict[str, Any]:
    hint = row.expo_push_token[-6:] if row.expo_push_token else ""
    registered = row.last_registered_at
    return {
        "id": str(row.id),
        "platform": row.platform,
        "device_name": row.device_name,
        "app_version": row.app_version,
        "is_active": row.is_active,
        "last_registered_at": registered.isoformat() if registered is not None else None,
        "disabled_reason": row.disabled_reason,
        "token_hint": hint,
    }


def _bind_existing(row: PushDeviceToken, ctx: OrganisationContext, body: PushDeviceRegister) -> PushDeviceToken:
    if row.user_id != ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Push token is already registered to another user",
        )
    row.organisation_id = ctx.organisation_id
    row.platform = body.platform
    row.device_name = body.device_name
    row.app_version = body.app_version
    row.is_active = True
    row.disabled_reason = None
    row.last_registered_at = _now()
    return row


def register_device(session: Session, ctx: OrganisationContext, body: PushDeviceRegister) -> dict[str, Any]:
    """Upsert by token. RLS is bypassed only for this lookup so a globally unique token can 409."""
    apply_platform_rls_bypass(session)
    try:
        return _register_token(session, ctx, body)
    finally:
        apply_organisation_rls(session, ctx.organisation_id)


def _register_token(session: Session, ctx: OrganisationContext, body: PushDeviceRegister) -> dict[str, Any]:
    existing = _find_token(session, body.expo_push_token)
    if existing is not None:
        _bind_existing(existing, ctx, body)
        session.flush()
        return _device_out(existing)

    row = PushDeviceToken(
        id=uuid.uuid4(),
        organisation_id=ctx.organisation_id,
        user_id=ctx.user_id,
        expo_push_token=body.expo_push_token,
        platform=body.platform,
        device_name=body.device_name,
        app_version=body.app_version,
        is_active=True,
        last_registered_at=_now(),
        disabled_reason=None,
    )
    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError:
        raced = _find_token(session, body.expo_push_token)
        if raced is None:
            raise
        _bind_existing(raced, ctx, body)
        session.flush()
        return _device_out(raced)
    return _device_out(row)


def list_own_devices(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(PushDeviceToken)
        .where(
            PushDeviceToken.organisation_id == ctx.organisation_id,
            PushDeviceToken.user_id == ctx.user_id,
        )
        .order_by(PushDeviceToken.last_registered_at.desc())
    ).all()
    return [_device_out(row) for row in rows]


def deactivate_device(session: Session, ctx: OrganisationContext, device_id: uuid.UUID) -> dict[str, Any]:
    row = session.get(PushDeviceToken, device_id)
    if row is None or not _owns(row, ctx):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    row.is_active = False
    row.disabled_reason = "user_deactivated"
    session.flush()
    return _device_out(row)
