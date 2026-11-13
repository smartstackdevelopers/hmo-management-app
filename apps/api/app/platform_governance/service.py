"""F8.12 platform governance service."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import __version__
from app.audit import events as audit_events
from app.audit.query import list_for_platform, list_for_org_context
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.audit import AuditEvent
from app.db.models.backup import BackupRun
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.db.models.governance import (
    GovernanceCompliancePolicy,
    GovernanceComplianceTask,
    GovernanceIncidentTimeline,
    GovernanceOrganisationRegistration,
    GovernanceSecurityAlert,
    GovernanceSecurityIncident,
    OrganisationGovernanceSettings,
    PlatformBrandingSettings,
)
from app.db.models.membership import OrganisationMembership
from app.db.models.organisation import Organisation
from app.db.models.privacy import PrivacyDataSubjectRequest
from app.db.models.user import User
from app.db.models.integration_hub import IntegrationWebhookDelivery
from app.platform_governance.ai_client import summarize_admin_activity
from app.platform_governance.constants import ADDON_DISCLAIMER, AI_NOTICE, COMPLIANCE_CATEGORIES
from app.rbac.context import AuthorizationContext
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.membership_service import create_organisation


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _org_settings(session: Session, org_id: UUID) -> OrganisationGovernanceSettings:
    row = session.scalars(
        select(OrganisationGovernanceSettings).where(OrganisationGovernanceSettings.organisation_id == org_id)
    ).first()
    if row is None:
        row = OrganisationGovernanceSettings(organisation_id=org_id)
        session.add(row)
        session.flush()
    return row


def assert_org_addon(session: Session, settings: Settings, org_id: UUID) -> OrganisationGovernanceSettings:
    if not settings.platform_governance_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Platform governance add-on disabled platform-wide")
    row = _org_settings(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Governance disabled for organisation")
    return row


def assert_platform_addon(settings: Settings) -> None:
    if not settings.platform_governance_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Platform governance add-on disabled platform-wide")


def _branding(session: Session) -> PlatformBrandingSettings:
    row = session.scalars(select(PlatformBrandingSettings).limit(1)).first()
    if row is None:
        row = PlatformBrandingSettings()
        session.add(row)
        session.flush()
    return row


def org_settings_dict(row: OrganisationGovernanceSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "notification_settings": row.notification_settings,
        "disclaimer": ADDON_DISCLAIMER,
    }


def platform_settings_dict(row: PlatformBrandingSettings) -> dict[str, Any]:
    return {
        "platform_name": row.platform_name,
        "branding_json": row.branding_json,
        "regional_settings": row.regional_settings,
        "security_settings": row.security_settings,
        "disclaimer": ADDON_DISCLAIMER,
    }


def update_org_settings(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> OrganisationGovernanceSettings:
    require_permission(ctx.authorization, Permission.PLATFORM_GOVERNANCE_MANAGE)
    row = assert_org_addon(session, get_settings(), ctx.organisation_id)
    for key in ("enabled", "privacy_review_complete"):
        if data.get(key) is not None:
            setattr(row, key, bool(data[key]))
    if data.get("notification_settings") is not None:
        row.notification_settings = data["notification_settings"]
    session.flush()
    record_event(
        session,
        action=audit_events.PLATFORM_GOVERNANCE_SETTINGS_UPDATE,
        resource_type="organisation_governance_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Organisation governance settings updated",
    )
    return row


def update_platform_branding(session: Session, authz: AuthorizationContext, data: dict[str, Any]) -> PlatformBrandingSettings:
    require_permission(authz, Permission.PLATFORM_SETTINGS_MANAGE)
    assert_platform_addon(get_settings())
    row = _branding(session)
    if data.get("platform_name"):
        row.platform_name = str(data["platform_name"])[:255]
    for key in ("branding_json", "regional_settings", "security_settings"):
        if data.get(key) is not None:
            setattr(row, key, data[key])
    session.flush()
    record_event(
        session,
        action=audit_events.PLATFORM_GOVERNANCE_BRANDING_UPDATE,
        resource_type="platform_branding_settings",
        resource_id=str(row.id),
        organisation_id=None,
        actor_user_id=authz.user.id if authz.user else None,
        actor_role=authz.active_role.value if authz.active_role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Platform branding settings updated",
    )
    return row


def _db_ping(session: Session) -> tuple[str, float | None]:
    started = time.perf_counter()
    try:
        session.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - started) * 1000, 2)
        return "ok", latency
    except Exception:
        return "unavailable", None


def system_health(session: Session, settings: Settings) -> dict[str, Any]:
    db_status, db_ms = _db_ping(session)
    celery_configured = bool(settings.redis_url)
    return {
        "api_version": __version__,
        "api_status": "ok",
        "database_status": db_status,
        "database_latency_ms": db_ms,
        "background_jobs_status": "configured" if celery_configured else "unavailable",
        "ai_gateway_status": "partial",
        "integration_hub_status": "enabled" if settings.integration_hub_global_enabled else "disabled",
        "notifications_status": "partial",
        "storage_status": "unavailable",
        "frontend_status": "unavailable",
    }


def platform_dashboard(session: Session, authz: AuthorizationContext) -> dict[str, Any]:
    require_permission(authz, Permission.PLATFORM_GOVERNANCE_READ)
    assert_platform_addon(get_settings())
    if authz.active_role != HMoreRole.SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Platform dashboard requires Super Admin")
    total_orgs = session.scalar(select(func.count()).select_from(Organisation)) or 0
    active_orgs = (
        session.scalar(select(func.count()).select_from(Organisation).where(Organisation.status == RecordStatus.ACTIVE))
        or 0
    )
    archived_orgs = total_orgs - active_orgs
    total_users = session.scalar(select(func.count()).select_from(User)) or 0
    active_memberships = (
        session.scalar(
            select(func.count()).select_from(OrganisationMembership).where(
                OrganisationMembership.status == MembershipStatus.ACTIVE
            )
        )
        or 0
    )
    pending_reg = (
        session.scalar(
            select(func.count()).select_from(GovernanceOrganisationRegistration).where(
                GovernanceOrganisationRegistration.status == "pending"
            )
        )
        or 0
    )
    open_incidents = (
        session.scalar(
            select(func.count()).select_from(GovernanceSecurityIncident).where(
                GovernanceSecurityIncident.status.in_(("open", "investigating"))
            )
        )
        or 0
    )
    open_alerts = (
        session.scalar(select(func.count()).select_from(GovernanceSecurityAlert).where(GovernanceSecurityAlert.status == "open"))
        or 0
    )
    auth_denied = (
        session.scalar(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.action == audit_events.AUTH_ACCESS_DENIED)
        )
        or 0
    )
    backup_ok = (
        session.scalar(
            select(func.count()).select_from(BackupRun).where(BackupRun.status.in_(("completed", "verified")))
        )
        or 0
    )
    backup_failed = (
        session.scalar(select(func.count()).select_from(BackupRun).where(BackupRun.status == "failed")) or 0
    )
    rows, _ = list_for_platform(session, authz, page=1, page_size=10)
    recent = [
        {
            "action": r.action,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    settings = get_settings()
    return {
        "total_organisations": int(total_orgs),
        "active_organisations": int(active_orgs),
        "suspended_organisations": int(archived_orgs),
        "total_users": int(total_users),
        "active_users": int(active_memberships),
        "pending_organisation_approvals": int(pending_reg),
        "open_security_incidents": int(open_incidents),
        "open_security_alerts": int(open_alerts),
        "security_events_auth_denied_total": int(auth_denied),
        "backup_runs_succeeded": int(backup_ok),
        "backup_runs_failed": int(backup_failed),
        "webhook_delivery_failures": int(
            session.scalar(
                select(func.count()).select_from(IntegrationWebhookDelivery).where(
                    IntegrationWebhookDelivery.status == "failed"
                )
            )
            or 0
        ),
        "system_health": system_health(session, settings),
        "recent_admin_activity": recent,
        "disclaimer": ADDON_DISCLAIMER,
    }


def organisation_dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.PLATFORM_GOVERNANCE_READ)
    assert_org_addon(session, get_settings(), ctx.organisation_id)
    org = ctx.organisation_id
    open_tasks = (
        session.scalar(
            select(func.count()).select_from(GovernanceComplianceTask).where(
                GovernanceComplianceTask.organisation_id == org,
                GovernanceComplianceTask.status == "open",
            )
        )
        or 0
    )
    policies = (
        session.scalar(
            select(func.count()).select_from(GovernanceCompliancePolicy).where(
                GovernanceCompliancePolicy.organisation_id == org
            )
        )
        or 0
    )
    pending_privacy = (
        session.scalar(
            select(func.count()).select_from(PrivacyDataSubjectRequest).where(
                PrivacyDataSubjectRequest.organisation_id == org,
                PrivacyDataSubjectRequest.status.not_in(("completed", "cancelled", "rejected")),
            )
        )
        or 0
    )
    open_incidents = (
        session.scalar(
            select(func.count()).select_from(GovernanceSecurityIncident).where(
                GovernanceSecurityIncident.organisation_id == org,
                GovernanceSecurityIncident.status.in_(("open", "investigating")),
            )
        )
        or 0
    )
    rows, _ = list_for_org_context(session, ctx, page=1, page_size=8)
    recent = [{"action": r.action, "summary": r.summary} for r in rows]
    return {
        "compliance_policies": int(policies),
        "open_compliance_tasks": int(open_tasks),
        "pending_privacy_requests": int(pending_privacy),
        "open_incidents": int(open_incidents),
        "recent_audit_activity": recent,
        "system_health": system_health(session, get_settings()),
        "disclaimer": ADDON_DISCLAIMER,
    }


def list_organisations(session: Session, authz: AuthorizationContext) -> list[dict[str, Any]]:
    require_permission(authz, Permission.PLATFORM_GOVERNANCE_MANAGE)
    assert_platform_addon(get_settings())
    rows = session.scalars(select(Organisation).order_by(Organisation.created_at.desc())).all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "slug": r.slug,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
        }
        for r in rows
    ]


def set_organisation_status(
    session: Session,
    authz: AuthorizationContext,
    organisation_id: UUID,
    new_status: RecordStatus,
) -> Organisation:
    require_permission(authz, Permission.PLATFORM_GOVERNANCE_MANAGE)
    assert_platform_addon(get_settings())
    org = session.get(Organisation, organisation_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    org.status = new_status
    session.flush()
    record_event(
        session,
        action=audit_events.PLATFORM_GOVERNANCE_ORG_STATUS,
        resource_type="organisation",
        resource_id=str(org.id),
        organisation_id=org.id,
        actor_user_id=authz.user.id if authz.user else None,
        actor_role=authz.active_role.value if authz.active_role else None,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Organisation status set to {new_status.value}",
    )
    return org


def submit_org_registration(
    session: Session,
    authz: AuthorizationContext,
    name: str,
    slug: str,
) -> GovernanceOrganisationRegistration:
    require_permission(authz, Permission.ORGANISATIONS_CREATE)
    assert_platform_addon(get_settings())
    row = GovernanceOrganisationRegistration(
        proposed_name=name,
        proposed_slug=slug.lower().strip(),
        status="pending",
        submitted_by_user_id=authz.user.id if authz.user else None,
    )
    session.add(row)
    session.flush()
    return row


def review_org_registration(
    session: Session,
    authz: AuthorizationContext,
    registration_id: UUID,
    *,
    approve: bool,
    notes: str | None,
) -> dict[str, Any]:
    require_permission(authz, Permission.PLATFORM_GOVERNANCE_MANAGE)
    row = session.get(GovernanceOrganisationRegistration, registration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Registration not found")
    if row.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Registration already reviewed")
    row.reviewed_at = _now()
    row.reviewed_by_user_id = authz.user.id if authz.user else None
    row.review_notes = notes
    if approve:
        org = create_organisation(session, actor=authz, name=row.proposed_name, slug=row.proposed_slug)
        row.status = "approved"
        session.flush()
        return {"status": "approved", "organisation_id": str(org.id)}
    row.status = "rejected"
    session.flush()
    return {"status": "rejected"}


def create_compliance_policy(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> GovernanceCompliancePolicy:
    require_permission(ctx.authorization, Permission.PLATFORM_GOVERNANCE_COMPLIANCE)
    assert_org_addon(session, get_settings(), ctx.organisation_id)
    row = GovernanceCompliancePolicy(
        organisation_id=ctx.organisation_id,
        category_slug=data["category_slug"],
        title=data["title"],
        owner_user_id=data.get("owner_user_id") or ctx.user_id,
        status=data.get("status", "draft"),
        policy_body=data.get("policy_body"),
    )
    session.add(row)
    session.flush()
    return row


def create_incident(session: Session, ctx: OrganisationContext | None, authz: AuthorizationContext, data: dict[str, Any]) -> GovernanceSecurityIncident:
    require_permission(authz, Permission.PLATFORM_GOVERNANCE_SECURITY)
    if ctx:
        assert_org_addon(session, get_settings(), ctx.organisation_id)
    row = GovernanceSecurityIncident(
        organisation_id=ctx.organisation_id if ctx else data.get("organisation_id"),
        severity=data.get("severity", "low"),
        category=data["category"],
        title=data["title"],
        description=data.get("description"),
        assigned_admin_user_id=data.get("assigned_admin_user_id"),
    )
    session.add(row)
    session.flush()
    session.add(
        GovernanceIncidentTimeline(
            incident_id=row.id,
            note="Incident created",
            actor_user_id=authz.user.id if authz.user else None,
        )
    )
    session.flush()
    return row


def list_categories() -> list[dict[str, str]]:
    return [{"slug": s, "label": label} for s, label in COMPLIANCE_CATEGORIES]


def sync_security_alerts_from_audit(session: Session, authz: AuthorizationContext, limit: int = 20) -> int:
    require_permission(authz, Permission.PLATFORM_GOVERNANCE_SECURITY)
    rows = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.action.in_((audit_events.AUTH_ACCESS_DENIED, audit_events.AUTH_TOKEN_INVALID)))
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    ).all()
    created = 0
    for ev in rows:
        exists = session.scalar(
            select(func.count()).select_from(GovernanceSecurityAlert).where(
                GovernanceSecurityAlert.source_audit_event_id == ev.id
            )
        )
        if exists:
            continue
        session.add(
            GovernanceSecurityAlert(
                organisation_id=ev.organisation_id,
                alert_type="auth_denied",
                severity="medium" if ev.action == audit_events.AUTH_ACCESS_DENIED else "high",
                summary=(ev.summary or ev.action)[:500],
                source_audit_event_id=ev.id,
            )
        )
        created += 1
    session.flush()
    return created


def ai_admin_summary(session: Session, ctx: OrganisationContext | None, authz: AuthorizationContext) -> dict[str, Any]:
    require_permission(authz, Permission.PLATFORM_GOVERNANCE_AI)
    settings_row = _org_settings(session, ctx.organisation_id) if ctx else OrganisationGovernanceSettings(enabled=False)
    if ctx:
        assert_org_addon(session, get_settings(), ctx.organisation_id)
    snippets: list[str] = []
    if ctx:
        rows, _ = list_for_org_context(session, ctx, page=1, page_size=5)
    else:
        rows, _ = list_for_platform(session, authz, page=1, page_size=5)
    snippets = [r.summary or r.action for r in rows if r.summary or r.action]
    result = summarize_admin_activity(enabled=settings_row.enabled or authz.active_role == HMoreRole.SUPER_ADMIN, audit_snippets=snippets)
    return {**result, "notice": AI_NOTICE}
