"""Organisation AI feature availability and configuration (F3.15).

Fail-closed rules:
- Missing configuration => unavailable.
- Service/DB errors during enforcement => unavailable (do not silently enable).
- Feature enablement never bypasses RBAC, budgets, or human approval.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai_feature_flags import access as ff_access
from app.ai_feature_flags.cache import TTL_SECONDS, cache_get, cache_invalidate, cache_set
from app.ai_feature_flags.registry import (
    CONTROLLABLE_FEATURE_IDS,
    REGISTRY,
    canonical_feature_id,
    get_definition,
    is_registered,
)
from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.ai_feature_flags import OrganisationAiFeatureFlag, OrganisationAiFeatureFlagHistory
from app.tenancy.context import OrganisationContext

logger = logging.getLogger("hmore.ai_feature_flags")

MAX_REASON = 2000


@dataclass(frozen=True)
class AvailabilityDecision:
    feature_id: str
    available: bool
    enabled: bool
    pilot_enabled: bool
    reason: str
    source: str  # config | missing | error | unregistered


def _public_flag(row: OrganisationAiFeatureFlag | None, feature_id: str) -> dict[str, Any]:
    definition = get_definition(feature_id)
    assert definition is not None
    if row is None:
        return {
            "feature_id": feature_id,
            "name": definition.name,
            "description": definition.description,
            "phase_feature": definition.phase_feature,
            "pilot_eligible": definition.pilot_eligible,
            "enabled": False,
            "pilot_enabled": False,
            "configured": False,
            "revision": None,
            "updated_at": None,
            "updated_by_user_id": None,
            "change_reason": None,
            "availability": "disabled_missing_config",
        }
    return {
        "feature_id": feature_id,
        "name": definition.name,
        "description": definition.description,
        "phase_feature": definition.phase_feature,
        "pilot_eligible": definition.pilot_eligible,
        "enabled": bool(row.enabled),
        "pilot_enabled": bool(row.pilot_enabled),
        "configured": True,
        "revision": row.revision,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "updated_by_user_id": str(row.updated_by_user_id) if row.updated_by_user_id else None,
        "change_reason": row.change_reason,
        "availability": "enabled"
        if row.enabled and (not definition.pilot_eligible or row.pilot_enabled)
        else "disabled",
    }


def evaluate_availability(
    session: Session,
    *,
    organisation_id: UUID,
    feature_id: str,
    use_cache: bool = True,
) -> AvailabilityDecision:
    """Central availability decision. Never silently enables on failure."""
    fid = canonical_feature_id(feature_id)
    if not is_registered(fid):
        return AvailabilityDecision(
            feature_id=fid,
            available=False,
            enabled=False,
            pilot_enabled=False,
            reason="unregistered_feature",
            source="unregistered",
        )

    definition = get_definition(fid)
    assert definition is not None

    if use_cache:
        cached = cache_get(organisation_id, fid)
        if cached is not None:
            enabled, pilot_enabled = cached
            available = enabled and (not definition.pilot_eligible or pilot_enabled)
            return AvailabilityDecision(
                feature_id=fid,
                available=available,
                enabled=enabled,
                pilot_enabled=pilot_enabled,
                reason="ok" if available else "disabled_or_pilot_required",
                source="config",
            )

    try:
        row = session.scalars(
            select(OrganisationAiFeatureFlag).where(
                OrganisationAiFeatureFlag.organisation_id == organisation_id,
                OrganisationAiFeatureFlag.feature_id == fid,
            )
        ).first()
    except Exception:  # noqa: BLE001
        logger.exception(
            "ai_feature_flag_lookup_failed org=%s feature=%s", organisation_id, fid
        )
        return AvailabilityDecision(
            feature_id=fid,
            available=False,
            enabled=False,
            pilot_enabled=False,
            reason="configuration_service_unavailable",
            source="error",
        )

    if row is None:
        # Fail closed — missing config is not enabled.
        cache_set(organisation_id, fid, enabled=False, pilot_enabled=False)
        return AvailabilityDecision(
            feature_id=fid,
            available=False,
            enabled=False,
            pilot_enabled=False,
            reason="missing_configuration",
            source="missing",
        )

    enabled = bool(row.enabled)
    pilot_enabled = bool(row.pilot_enabled)
    cache_set(organisation_id, fid, enabled=enabled, pilot_enabled=pilot_enabled)
    available = enabled and (not definition.pilot_eligible or pilot_enabled)
    return AvailabilityDecision(
        feature_id=fid,
        available=available,
        enabled=enabled,
        pilot_enabled=pilot_enabled,
        reason="ok" if available else "disabled_or_pilot_required",
        source="config",
    )


def is_feature_available(
    session: Session, *, organisation_id: UUID, feature_id: str, use_cache: bool = True
) -> bool:
    return evaluate_availability(
        session, organisation_id=organisation_id, feature_id=feature_id, use_cache=use_cache
    ).available


def require_feature_available(
    session: Session,
    ctx: OrganisationContext,
    feature_id: str,
    *,
    audit_block: bool = True,
) -> AvailabilityDecision:
    """Raise 403 if the org cannot use the feature. Call before AI execution."""
    decision = evaluate_availability(
        session, organisation_id=ctx.organisation_id, feature_id=feature_id
    )
    if decision.available:
        return decision

    if audit_block:
        record_event(
            session,
            action=audit_events.AI_FEATURE_EXECUTION_BLOCKED,
            resource_type="organisation_ai_feature_flag",
            resource_id=decision.feature_id,
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.DENIED,
            summary=f"AI feature blocked: {decision.feature_id}",
            metadata={
                "feature_id": decision.feature_id,
                "reason": decision.reason,
                "source": decision.source,
                "enabled": decision.enabled,
                "pilot_enabled": decision.pilot_enabled,
            },
            raise_on_error=False,
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "ai_feature_disabled",
            "feature_id": decision.feature_id,
            "reason": decision.reason,
            "message": (
                "This AI feature is not enabled for your organisation. "
                "Contact an organisation administrator."
            ),
        },
    )


def list_registry() -> list[dict[str, Any]]:
    return [
        {
            "feature_id": f.feature_id,
            "name": f.name,
            "description": f.description,
            "phase_feature": f.phase_feature,
            "pilot_eligible": f.pilot_eligible,
        }
        for f in REGISTRY
    ]


def list_organisation_config(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    ff_access.require_read(ctx)
    rows = list(
        session.scalars(
            select(OrganisationAiFeatureFlag).where(
                OrganisationAiFeatureFlag.organisation_id == ctx.organisation_id
            )
        )
    )
    by_id = {r.feature_id: r for r in rows}
    items = [_public_flag(by_id.get(f.feature_id), f.feature_id) for f in REGISTRY]
    return {
        "organisation_id": str(ctx.organisation_id),
        "items": items,
        "cache_ttl_seconds": TTL_SECONDS,
        "defaults_note": (
            "Missing configuration means the feature is disabled. "
            "New organisations start with all controllable AI features disabled."
        ),
    }


def get_feature_config(
    session: Session, ctx: OrganisationContext, feature_id: str
) -> dict[str, Any]:
    ff_access.require_read(ctx)
    fid = canonical_feature_id(feature_id)
    if not is_registered(fid):
        raise HTTPException(status_code=422, detail="Unsupported AI feature identifier")
    row = session.scalars(
        select(OrganisationAiFeatureFlag).where(
            OrganisationAiFeatureFlag.organisation_id == ctx.organisation_id,
            OrganisationAiFeatureFlag.feature_id == fid,
        )
    ).first()
    return _public_flag(row, fid)


def _append_history(
    session: Session,
    *,
    organisation_id: UUID,
    feature_id: str,
    flag_id: UUID | None,
    actor_user_id: UUID | None,
    previous_enabled: bool | None,
    previous_pilot: bool | None,
    new_enabled: bool,
    new_pilot: bool,
    change_reason: str | None,
    action: str,
    revision: int,
) -> None:
    session.add(
        OrganisationAiFeatureFlagHistory(
            id=uuid.uuid4(),
            organisation_id=organisation_id,
            feature_id=feature_id,
            flag_id=flag_id,
            actor_user_id=actor_user_id,
            previous_enabled=previous_enabled,
            previous_pilot_enabled=previous_pilot,
            new_enabled=new_enabled,
            new_pilot_enabled=new_pilot,
            change_reason=change_reason,
            action=action,
            revision=revision,
        )
    )


def update_feature(
    session: Session,
    ctx: OrganisationContext,
    feature_id: str,
    *,
    enabled: bool,
    pilot_enabled: bool | None = None,
    change_reason: str | None = None,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    """Enable/disable a registered feature for the active organisation only."""
    try:
        ff_access.require_manage(ctx)
    except HTTPException:
        record_event(
            session,
            action=audit_events.AI_FEATURE_CONFIG_REJECTED,
            resource_type="organisation_ai_feature_flag",
            resource_id=feature_id,
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.DENIED,
            summary="Unauthorised AI feature configuration attempt",
            metadata={"feature_id": feature_id},
            raise_on_error=False,
        )
        raise

    fid = canonical_feature_id(feature_id)
    if not is_registered(fid):
        raise HTTPException(status_code=422, detail="Unsupported AI feature identifier")
    if fid not in CONTROLLABLE_FEATURE_IDS:
        raise HTTPException(status_code=422, detail="Feature is not organisation-controllable")

    definition = get_definition(fid)
    assert definition is not None

    reason = (change_reason or "").strip().replace("\x00", "")[:MAX_REASON] or None
    if reason is None and (enabled is False or (pilot_enabled is False)):
        # Encourage reasons for disable; not hard-required for enable.
        pass

    row = session.scalars(
        select(OrganisationAiFeatureFlag).where(
            OrganisationAiFeatureFlag.organisation_id == ctx.organisation_id,
            OrganisationAiFeatureFlag.feature_id == fid,
        )
    ).first()

    if expected_revision is not None:
        current_rev = row.revision if row is not None else 0
        if current_rev != expected_revision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "revision_conflict",
                    "expected": expected_revision,
                    "current": current_rev,
                },
            )

    previous_enabled = bool(row.enabled) if row else None
    previous_pilot = bool(row.pilot_enabled) if row else None

    # Pilot-eligible: explicit pilot_enabled wins; omitted on first enable defaults pilot on.
    if not definition.pilot_eligible:
        resolved_pilot = bool(pilot_enabled) if pilot_enabled is not None else False
    elif pilot_enabled is not None:
        resolved_pilot = bool(pilot_enabled)
    elif row is not None:
        resolved_pilot = bool(row.pilot_enabled)
    else:
        resolved_pilot = bool(enabled)

    created = row is None
    if row is None:
        row = OrganisationAiFeatureFlag(
            id=uuid.uuid4(),
            organisation_id=ctx.organisation_id,
            feature_id=fid,
            enabled=bool(enabled),
            pilot_enabled=resolved_pilot,
            change_reason=reason,
            updated_by_user_id=ctx.user_id,
            revision=1,
        )
        session.add(row)
        try:
            session.flush()
        except IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Concurrent configuration create") from exc
        action = "created"
    else:
        row.enabled = bool(enabled)
        row.pilot_enabled = resolved_pilot
        row.change_reason = reason
        row.updated_by_user_id = ctx.user_id
        row.revision = int(row.revision) + 1
        session.flush()
        action = "updated"

    _append_history(
        session,
        organisation_id=ctx.organisation_id,
        feature_id=fid,
        flag_id=row.id,
        actor_user_id=ctx.user_id,
        previous_enabled=previous_enabled,
        previous_pilot=previous_pilot,
        new_enabled=row.enabled,
        new_pilot=row.pilot_enabled,
        change_reason=reason,
        action=action,
        revision=row.revision,
    )
    session.flush()
    cache_invalidate(ctx.organisation_id, fid)

    # Audit granular enable/disable/pilot events.
    if created:
        audit_action = audit_events.AI_FEATURE_CONFIG_CREATED
    elif previous_enabled is False and row.enabled:
        audit_action = audit_events.AI_FEATURE_ENABLED
    elif previous_enabled is True and not row.enabled:
        audit_action = audit_events.AI_FEATURE_DISABLED
    elif previous_pilot is False and row.pilot_enabled:
        audit_action = audit_events.AI_FEATURE_PILOT_ENABLED
    elif previous_pilot is True and not row.pilot_enabled:
        audit_action = audit_events.AI_FEATURE_PILOT_DISABLED
    else:
        audit_action = audit_events.AI_FEATURE_CONFIG_UPDATED

    record_event(
        session,
        action=audit_action,
        resource_type="organisation_ai_feature_flag",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"AI feature {fid} {action}",
        metadata={
            "feature_id": fid,
            "previous_enabled": previous_enabled,
            "previous_pilot_enabled": previous_pilot,
            "new_enabled": row.enabled,
            "new_pilot_enabled": row.pilot_enabled,
            "revision": row.revision,
            "change_reason": reason,
            "bypasses_usage_caps": False,
            "bypasses_human_approval": False,
        },
        raise_on_error=False,
    )
    return _public_flag(row, fid)


def list_history(
    session: Session,
    ctx: OrganisationContext,
    *,
    feature_id: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    ff_access.require_read(ctx)
    limit = max(1, min(limit, 100))
    clauses = [OrganisationAiFeatureFlagHistory.organisation_id == ctx.organisation_id]
    if feature_id:
        fid = canonical_feature_id(feature_id)
        if not is_registered(fid):
            raise HTTPException(status_code=422, detail="Unsupported AI feature identifier")
        clauses.append(OrganisationAiFeatureFlagHistory.feature_id == fid)
    rows = list(
        session.scalars(
            select(OrganisationAiFeatureFlagHistory)
            .where(*clauses)
            .order_by(OrganisationAiFeatureFlagHistory.event_at.desc())
            .limit(limit)
        )
    )
    return {
        "items": [
            {
                "id": str(r.id),
                "feature_id": r.feature_id,
                "action": r.action,
                "previous_enabled": r.previous_enabled,
                "previous_pilot_enabled": r.previous_pilot_enabled,
                "new_enabled": r.new_enabled,
                "new_pilot_enabled": r.new_pilot_enabled,
                "change_reason": r.change_reason,
                "revision": r.revision,
                "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
                "event_at": r.event_at.isoformat() if r.event_at else None,
            }
            for r in rows
        ]
    }


def seed_defaults_for_organisation(
    session: Session,
    *,
    organisation_id: UUID,
    actor_user_id: UUID | None = None,
    tenant_assistant_pilot: bool = False,
) -> int:
    """Seed safe defaults for a newly created organisation (all disabled).

    Tenant Assistant remains disabled unless tenant_assistant_pilot=True.
    Returns number of rows created.
    """
    created = 0
    for definition in REGISTRY:
        exists = session.scalars(
            select(OrganisationAiFeatureFlag.id).where(
                OrganisationAiFeatureFlag.organisation_id == organisation_id,
                OrganisationAiFeatureFlag.feature_id == definition.feature_id,
            )
        ).first()
        if exists:
            continue
        enabled = False
        pilot = False
        if definition.feature_id == "ai.agent.tenant_assistant" and tenant_assistant_pilot:
            enabled = True
            pilot = True
        row = OrganisationAiFeatureFlag(
            id=uuid.uuid4(),
            organisation_id=organisation_id,
            feature_id=definition.feature_id,
            enabled=enabled,
            pilot_enabled=pilot,
            change_reason="default_assignment_new_organisation",
            updated_by_user_id=actor_user_id,
            revision=1,
        )
        session.add(row)
        session.flush()
        _append_history(
            session,
            organisation_id=organisation_id,
            feature_id=definition.feature_id,
            flag_id=row.id,
            actor_user_id=actor_user_id,
            previous_enabled=None,
            previous_pilot=None,
            new_enabled=enabled,
            new_pilot=pilot,
            change_reason="default_assignment_new_organisation",
            action="default_assigned",
            revision=1,
        )
        created += 1
    if created:
        cache_invalidate(organisation_id)
        record_event(
            session,
            action=audit_events.AI_FEATURE_DEFAULTS_ASSIGNED,
            resource_type="organisation",
            resource_id=str(organisation_id),
            organisation_id=organisation_id,
            actor_user_id=actor_user_id,
            actor_role=None,
            outcome=AuditOutcome.SUCCESS,
            summary="Default AI feature flags assigned (disabled unless pilot)",
            metadata={"created": created},
            raise_on_error=False,
        )
    return created
