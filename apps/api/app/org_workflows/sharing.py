"""Secure sharing grants (token hash, expiry, revocation)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.org_workflows import SecureSharingAccessLog, SecureSharingGrant
from app.org_workflows import notify
from app.org_workflows.access import require_sharing_grant, require_sharing_read, require_sharing_revoke
from app.org_workflows.schemas import SharingGrantCreate, SharingRevoke
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _next_ref(session: Session, org_id: uuid.UUID) -> str:
    n = session.scalar(select(func.count()).select_from(SecureSharingGrant).where(SecureSharingGrant.organisation_id == org_id)) or 0
    return f"SHARE-{n + 1:06d}"


def _audit(session: Session, ctx: OrganisationContext, action: str, rid: uuid.UUID, summary: str, meta: dict | None = None) -> None:
    record_event(
        session,
        action=action,
        resource_type="secure_sharing_grant",
        resource_id=str(rid),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=summary,
        metadata=meta or {},
        raise_on_error=False,
    )


def _serialize(grant: SecureSharingGrant) -> dict[str, Any]:
    return {
        "id": str(grant.id),
        "reference_number": grant.reference_number,
        "resource_type": grant.resource_type,
        "resource_id": str(grant.resource_id),
        "recipient_user_id": str(grant.recipient_user_id) if grant.recipient_user_id else None,
        "purpose": grant.purpose,
        "scope": grant.scope_json,
        "expires_at": grant.expires_at.isoformat(),
        "status": grant.status,
        "revoked_at": grant.revoked_at.isoformat() if grant.revoked_at else None,
        "created_at": grant.created_at.isoformat() if grant.created_at else None,
    }


def create_grant(session: Session, ctx: OrganisationContext, body: SharingGrantCreate) -> dict[str, Any]:
    require_sharing_grant(ctx)
    if body.expires_at <= _now():
        raise HTTPException(status_code=400, detail="Expiry must be in the future")
    token = secrets.token_urlsafe(32)
    grant = SecureSharingGrant(
        organisation_id=ctx.organisation_id,
        reference_number=_next_ref(session, ctx.organisation_id),
        resource_type=body.resource_type.strip(),
        resource_id=body.resource_id,
        recipient_user_id=body.recipient_user_id,
        recipient_organisation_id=body.recipient_organisation_id,
        purpose=body.purpose.strip(),
        scope_json=body.scope,
        expires_at=body.expires_at,
        token_hash=_token_hash(token),
        status="active",
        created_by_user_id=ctx.user_id,
    )
    session.add(grant)
    session.flush()
    _audit(session, ctx, audit_events.SECURE_SHARING_CREATE, grant.id, "Sharing grant created")
    notify.sharing_granted(session, ctx, body.recipient_user_id, grant.id, grant.reference_number)
    session.flush()
    out = _serialize(grant)
    out["access_token"] = token
    return out


def list_grants(session: Session, ctx: OrganisationContext, *, active_only: bool = True) -> list[dict[str, Any]]:
    require_sharing_read(ctx)
    stmt = select(SecureSharingGrant).where(SecureSharingGrant.organisation_id == ctx.organisation_id)
    if active_only:
        stmt = stmt.where(SecureSharingGrant.status == "active")
    rows = session.scalars(stmt.order_by(SecureSharingGrant.created_at.desc())).all()
    return [_serialize(g) for g in rows]


def get_grant(session: Session, ctx: OrganisationContext, grant_id: uuid.UUID) -> dict[str, Any]:
    require_sharing_read(ctx)
    grant = session.get(SecureSharingGrant, grant_id)
    if grant is None or grant.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Not found")
    return _serialize(grant)


def revoke_grant(
    session: Session, ctx: OrganisationContext, grant_id: uuid.UUID, body: SharingRevoke | None
) -> dict[str, Any]:
    require_sharing_revoke(ctx)
    grant = session.get(SecureSharingGrant, grant_id)
    if grant is None or grant.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Not found")
    if grant.revoked_at is not None:
        raise HTTPException(status_code=409, detail="Already revoked")
    grant.revoked_at = _now()
    grant.revoked_by_user_id = ctx.user_id
    grant.status = "revoked"
    _audit(
        session,
        ctx,
        audit_events.SECURE_SHARING_REVOKE,
        grant.id,
        "Sharing revoked",
        {"reason": body.reason if body else None},
    )
    notify.sharing_revoked(session, ctx, grant.recipient_user_id, grant.id)
    session.flush()
    return _serialize(grant)


def access_by_token(
    session: Session,
    ctx: OrganisationContext,
    token: str,
    *,
    client_ip: str | None = None,
) -> dict[str, Any]:
    """Validate token and return scoped resource reference (not storage paths)."""
    require_sharing_read(ctx)
    digest = _token_hash(token)
    grant = session.scalar(
        select(SecureSharingGrant).where(
            SecureSharingGrant.organisation_id == ctx.organisation_id,
            SecureSharingGrant.token_hash == digest,
        )
    )
    outcome = "denied"
    if grant is None:
        raise HTTPException(status_code=403, detail="Invalid or expired grant")
    now = _now()
    if grant.revoked_at is not None or grant.status == "revoked":
        outcome = "revoked"
    elif grant.expires_at < now:
        grant.status = "expired"
        outcome = "expired"
    else:
        outcome = "allowed"
    session.add(
        SecureSharingAccessLog(
            organisation_id=ctx.organisation_id,
            grant_id=grant.id,
            accessor_user_id=ctx.user_id,
            outcome=outcome,
            client_ip=client_ip,
        )
    )
    if outcome != "allowed":
        session.flush()
        raise HTTPException(status_code=403, detail=f"Grant {outcome}")
    _audit(session, ctx, audit_events.SECURE_SHARING_ACCESS, grant.id, "Token access", {"outcome": outcome})
    session.flush()
    return {
        "grant_id": str(grant.id),
        "resource_type": grant.resource_type,
        "resource_id": str(grant.resource_id),
        "scope": grant.scope_json,
        "expires_at": grant.expires_at.isoformat(),
    }
