"""F6.7 Council Portal — shares, officers, sanitized application views."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.council_portal import access
from app.council_portal.constants import ALLOWED_SCOPES, PORTAL_DISCLAIMER
from app.council_portal.context import CouncilPortalContext
from app.db.models.council_portal import (
    CouncilPortalAccessLog,
    CouncilPortalOfficer,
    CouncilPortalShare,
)
from app.db.models.evidence import EvidencePack
from app.db.models.housing import (
    HousingApplication,
    HousingApplicationDecision,
    HousingApplicationStatusHistory,
)
from app.db.models.user import User
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log_access(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    officer_user_id: uuid.UUID | None,
    share_id: uuid.UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    outcome: str = "success",
    summary: str | None = None,
) -> None:
    session.add(
        CouncilPortalAccessLog(
            organisation_id=organisation_id,
            officer_user_id=officer_user_id,
            share_id=share_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            summary=(summary or "")[:500] or None,
        )
    )


def officer_to_dict(row: CouncilPortalOfficer) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "user_id": str(row.user_id),
        "addon_role_label": row.addon_role_label,
        "status": row.status,
        "display_name": row.display_name,
        "council_organisation_name": row.council_organisation_name,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "isolation_note": "Council officer is an add-on identity; not stored in hmore_role / organisation_memberships.",
    }


def share_to_dict(row: CouncilPortalShare) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "application_id": str(row.application_id),
        "resource_type": row.resource_type,
        "resource_id": str(row.resource_id),
        "purpose": row.purpose,
        "scope": row.scope_json or {},
        "status": row.status,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "include_evidence": row.include_evidence,
        "include_approval_history": row.include_approval_history,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def invite_officer(
    session: Session,
    ctx: OrganisationContext,
    *,
    user_id: uuid.UUID,
    display_name: str | None = None,
    council_organisation_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    access.require_council_portal_manage(ctx)
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    row = CouncilPortalOfficer(
        organisation_id=ctx.organisation_id,
        user_id=user_id,
        addon_role_label="council_officer",
        status="active",
        display_name=display_name or user.display_name,
        council_organisation_name=council_organisation_name,
        invited_by_user_id=ctx.user_id,
        notes=notes,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Officer already registered for this organisation") from exc
    record_event(
        session,
        action=audit_events.COUNCIL_PORTAL_OFFICER_INVITE,
        resource_type="council_portal_officer",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Invited council portal officer (add-on role)",
        metadata={"addon_role_label": "council_officer"},
        raise_on_error=False,
    )
    return officer_to_dict(row)


def list_officers(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    access.require_council_portal_manage(ctx)
    rows = session.scalars(
        select(CouncilPortalOfficer)
        .where(CouncilPortalOfficer.organisation_id == ctx.organisation_id)
        .order_by(CouncilPortalOfficer.created_at.desc())
    ).all()
    return [officer_to_dict(r) for r in rows]


def set_officer_status(
    session: Session, ctx: OrganisationContext, officer_id: uuid.UUID, status: str
) -> dict[str, Any]:
    access.require_council_portal_manage(ctx)
    if status not in {"active", "suspended", "revoked"}:
        raise HTTPException(status_code=400, detail="Invalid officer status")
    row = session.get(CouncilPortalOfficer, officer_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Officer not found")
    row.status = status
    session.flush()
    return officer_to_dict(row)


def create_share(
    session: Session,
    ctx: OrganisationContext,
    *,
    application_id: uuid.UUID,
    purpose: str,
    include_evidence: bool = False,
    include_approval_history: bool = True,
    scopes: list[str] | None = None,
    expires_at: datetime | None = None,
    evidence_pack_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    access.require_council_portal_manage(ctx)
    if not purpose.strip():
        raise HTTPException(status_code=400, detail="Purpose is required")
    app = session.get(HousingApplication, application_id)
    if app is None or app.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status == "draft":
        raise HTTPException(status_code=400, detail="Draft applications cannot be shared with council")

    cleaned_scopes = {s for s in (scopes or ["application_status", "approval_history"]) if s in ALLOWED_SCOPES}
    if not cleaned_scopes:
        cleaned_scopes = {"application_status"}
    resource_type = "housing_application"
    resource_id = app.id
    if include_evidence and evidence_pack_id is not None:
        pack = session.get(EvidencePack, evidence_pack_id)
        if pack is None or pack.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=404, detail="Evidence pack not found")
        # Keep primary share on application; evidence flag gates meta listing
        cleaned_scopes.add("evidence_meta")

    row = CouncilPortalShare(
        organisation_id=ctx.organisation_id,
        application_id=app.id,
        resource_type=resource_type,
        resource_id=resource_id,
        purpose=purpose.strip()[:2000],
        scope_json={k: True for k in cleaned_scopes},
        status="active",
        expires_at=expires_at,
        created_by_user_id=ctx.user_id,
        include_evidence=include_evidence,
        include_approval_history=include_approval_history,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Active share already exists for this application") from exc
    record_event(
        session,
        action=audit_events.COUNCIL_PORTAL_SHARE_CREATE,
        resource_type="council_portal_share",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Shared application {app.reference_number} with Council Portal",
        raise_on_error=False,
    )
    return share_to_dict(row)


def list_shares(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    access.require_council_portal_manage(ctx)
    rows = session.scalars(
        select(CouncilPortalShare)
        .where(CouncilPortalShare.organisation_id == ctx.organisation_id)
        .order_by(CouncilPortalShare.created_at.desc())
    ).all()
    return [share_to_dict(r) for r in rows]


def revoke_share(session: Session, ctx: OrganisationContext, share_id: uuid.UUID) -> dict[str, Any]:
    access.require_council_portal_manage(ctx)
    row = session.get(CouncilPortalShare, share_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Share not found")
    row.status = "revoked"
    row.revoked_at = _now()
    row.revoked_by_user_id = ctx.user_id
    session.flush()
    record_event(
        session,
        action=audit_events.COUNCIL_PORTAL_SHARE_REVOKE,
        resource_type="council_portal_share",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Revoked council portal share",
        raise_on_error=False,
    )
    return share_to_dict(row)


def _active_share(session: Session, organisation_id: uuid.UUID, share_id: uuid.UUID) -> CouncilPortalShare:
    row = session.get(CouncilPortalShare, share_id)
    if row is None or row.organisation_id != organisation_id:
        raise HTTPException(status_code=404, detail="Share not found")
    if row.status != "active":
        raise HTTPException(status_code=403, detail="Share is not active")
    if row.expires_at and row.expires_at <= _now():
        row.status = "expired"
        session.flush()
        raise HTTPException(status_code=403, detail="Share has expired")
    return row


def _sanitize_application(app: HousingApplication, share: CouncilPortalShare) -> dict[str, Any]:
    """Never expose full tenant PII — reference + status fields only unless scoped."""
    out: dict[str, Any] = {
        "application_id": str(app.id),
        "reference_number": app.reference_number,
        "status": app.status if (share.scope_json or {}).get("application_status", True) else None,
        "priority": app.priority,
        "accommodation_type": app.accommodation_type,
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        "decided_at": app.decided_at.isoformat() if app.decided_at else None,
        "share_id": str(share.id),
        "purpose": share.purpose,
        "tenant_records_exposed": False,
        "disclaimer": PORTAL_DISCLAIMER,
    }
    # High-level requirements only — no household personal identifiers
    if (share.scope_json or {}).get("application_status", True):
        out["housing_requirements_summary"] = (app.housing_requirements or "")[:500]
    return out


def officer_inbox(session: Session, cctx: CouncilPortalContext) -> dict[str, Any]:
    rows = session.scalars(
        select(CouncilPortalShare).where(
            CouncilPortalShare.organisation_id == cctx.organisation_id,
            CouncilPortalShare.status == "active",
        )
    ).all()
    items = []
    for share in rows:
        if share.expires_at and share.expires_at <= _now():
            continue
        app = session.get(HousingApplication, share.application_id)
        if app is None:
            continue
        items.append(_sanitize_application(app, share))
    _log_access(
        session,
        organisation_id=cctx.organisation_id,
        officer_user_id=cctx.user_id,
        share_id=None,
        action="council_portal.inbox.view",
        summary=f"Viewed {len(items)} shared applications",
    )
    session.flush()
    record_event(
        session,
        action=audit_events.COUNCIL_PORTAL_VIEW,
        resource_type="council_portal_inbox",
        organisation_id=cctx.organisation_id,
        actor_user_id=cctx.user_id,
        outcome=AuditOutcome.SUCCESS,
        summary="Council officer viewed shared applications inbox",
        metadata={"addon_role": cctx.addon_role_label, "count": len(items)},
        raise_on_error=False,
    )
    return {"items": items, "disclaimer": PORTAL_DISCLAIMER, "addon_role_label": cctx.addon_role_label}


def officer_get_application(
    session: Session, cctx: CouncilPortalContext, share_id: uuid.UUID
) -> dict[str, Any]:
    share = _active_share(session, cctx.organisation_id, share_id)
    app = session.get(HousingApplication, share.application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    payload = _sanitize_application(app, share)

    if share.include_approval_history and (share.scope_json or {}).get("approval_history", True):
        history = session.scalars(
            select(HousingApplicationStatusHistory)
            .where(HousingApplicationStatusHistory.application_id == app.id)
            .order_by(HousingApplicationStatusHistory.created_at.asc())
        ).all()
        decisions = session.scalars(
            select(HousingApplicationDecision).where(HousingApplicationDecision.application_id == app.id)
        ).all()
        payload["approval_history"] = [
            {
                "from_status": h.from_status,
                "to_status": h.to_status,
                "at": h.created_at.isoformat() if h.created_at else None,
                "note": h.note,
            }
            for h in history
        ]
        payload["decisions"] = [
            {
                "decision": d.decision if hasattr(d, "decision") else getattr(d, "outcome", None),
                "at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in decisions
        ]

    if share.include_evidence and (share.scope_json or {}).get("evidence_meta", False):
        packs = session.scalars(
            select(EvidencePack).where(
                EvidencePack.organisation_id == cctx.organisation_id,
                EvidencePack.application_id == app.id,
            )
        ).all()
        payload["evidence_packs"] = [
            {
                "id": str(p.id),
                "status": p.status,
                "is_complete": p.is_complete,
                "generated_at": p.generated_at.isoformat() if p.generated_at else None,
                "content_bytes_exposed": False,
            }
            for p in packs
        ]

    _log_access(
        session,
        organisation_id=cctx.organisation_id,
        officer_user_id=cctx.user_id,
        share_id=share.id,
        action="council_portal.application.view",
        resource_type="housing_application",
        resource_id=app.id,
        summary=f"Viewed shared application {app.reference_number}",
    )
    session.flush()
    record_event(
        session,
        action=audit_events.COUNCIL_PORTAL_VIEW,
        resource_type="housing_application",
        resource_id=app.id,
        organisation_id=cctx.organisation_id,
        actor_user_id=cctx.user_id,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Council officer viewed {app.reference_number}",
        metadata={"share_id": str(share.id), "addon_role": cctx.addon_role_label},
        raise_on_error=False,
    )
    return payload


def officer_report_summary(session: Session, cctx: CouncilPortalContext) -> dict[str, Any]:
    """Council-related reporting: counts of shared applications by status only."""
    shares = session.scalars(
        select(CouncilPortalShare).where(
            CouncilPortalShare.organisation_id == cctx.organisation_id,
            CouncilPortalShare.status == "active",
        )
    ).all()
    by_status: dict[str, int] = {}
    for share in shares:
        app = session.get(HousingApplication, share.application_id)
        if app is None:
            continue
        by_status[app.status] = by_status.get(app.status, 0) + 1
    _log_access(
        session,
        organisation_id=cctx.organisation_id,
        officer_user_id=cctx.user_id,
        share_id=None,
        action="council_portal.report.view",
        summary="Viewed council shared-application report",
    )
    session.flush()
    return {
        "shared_application_count": sum(by_status.values()),
        "by_status": by_status,
        "disclaimer": PORTAL_DISCLAIMER,
        "note": "Report covers only explicitly shared applications — not organisation-wide caseload.",
    }


def admin_dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    access.require_council_portal_manage(ctx)
    officers = int(
        session.scalar(
            select(func.count())
            .select_from(CouncilPortalOfficer)
            .where(
                CouncilPortalOfficer.organisation_id == ctx.organisation_id,
                CouncilPortalOfficer.status == "active",
            )
        )
        or 0
    )
    shares = int(
        session.scalar(
            select(func.count())
            .select_from(CouncilPortalShare)
            .where(
                CouncilPortalShare.organisation_id == ctx.organisation_id,
                CouncilPortalShare.status == "active",
            )
        )
        or 0
    )
    return {
        "disclaimer": PORTAL_DISCLAIMER,
        "active_officers": officers,
        "active_shares": shares,
        "core_roles_unchanged": True,
        "addon_role_label": "council_officer",
        "officers": list_officers(session, ctx)[:20],
        "shares": list_shares(session, ctx)[:20],
    }
