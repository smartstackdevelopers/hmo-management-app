"""Emergency access grant logging. Does not grant elevated permissions."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.redaction import sanitize_reason
from app.audit.service import AuditOutcome, record_event
from app.db.models.emergency_access import EmergencyAccess
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation

ALLOWED_STATUSES = frozenset(
    {"requested", "approved", "rejected", "active", "expired", "revoked"}
)
MAX_DURATION_HOURS = 72


def request_emergency_access(
    session: Session,
    ctx: OrganisationContext,
    *,
    reason: str,
    duration_hours: int = 4,
    resource_type: str | None = None,
    resource_id: str | None = None,
    correlation_id: str | None = None,
) -> EmergencyAccess:
    if duration_hours < 1 or duration_hours > MAX_DURATION_HOURS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"duration_hours must be between 1 and {MAX_DURATION_HOURS}",
        )
    safe_reason = sanitize_reason(reason)
    now = datetime.now(timezone.utc)
    grant = EmergencyAccess(
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        status="requested",
        reason=safe_reason,
        resource_type=resource_type,
        resource_id=resource_id,
        expires_at=now + timedelta(hours=duration_hours),
    )
    session.add(grant)
    session.flush()
    record_event(
        session,
        action=audit_events.EMERGENCY_REQUESTED,
        resource_type="emergency_access",
        resource_id=grant.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        correlation_id=correlation_id,
        summary="Emergency access requested",
        metadata={
            "duration_hours": duration_hours,
            "target_resource_type": resource_type,
            "target_resource_id": resource_id,
        },
    )
    return grant


def transition_emergency_access(
    session: Session,
    ctx: OrganisationContext,
    grant_id: uuid.UUID,
    *,
    new_status: str,
    correlation_id: str | None = None,
) -> EmergencyAccess:
    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
    grant = session.get(EmergencyAccess, grant_id)
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")
    assert_same_organisation(ctx, grant.organisation_id)

    action_map = {
        "approved": audit_events.EMERGENCY_APPROVED,
        "rejected": audit_events.EMERGENCY_REJECTED,
        "active": audit_events.EMERGENCY_ACTIVATED,
        "expired": audit_events.EMERGENCY_EXPIRED,
        "revoked": audit_events.EMERGENCY_REVOKED,
        "requested": audit_events.EMERGENCY_REQUESTED,
    }
    now = datetime.now(timezone.utc)
    grant.status = new_status
    if new_status == "approved":
        grant.approved_by_user_id = ctx.user_id
    if new_status == "active":
        grant.activated_at = now
    if new_status == "revoked":
        grant.revoked_at = now
    if new_status == "expired" and grant.expires_at > now:
        grant.expires_at = now
    session.add(grant)
    session.flush()
    record_event(
        session,
        action=action_map[new_status],
        resource_type="emergency_access",
        resource_id=grant.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        correlation_id=correlation_id,
        summary=f"Emergency access marked {new_status}",
        metadata={"status": new_status},
    )
    return grant
