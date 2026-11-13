"""F8.2 safeguarding alerts orchestration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai_usage import features as ai_features
from app.ai_usage.metering import record_and_reconcile
from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.enums import HMoreRole
from app.db.models.safeguarding_alerts import (
    OrganisationSafeguardingAlertSettings,
    SafeguardingAlert,
    SafeguardingAlertAiSuggestion,
    SafeguardingAlertCategory,
    SafeguardingAlertEscalation,
    SafeguardingAlertReview,
    SafeguardingAlertRule,
    SafeguardingAlertStatusHistory,
    SafeguardingTenantReport,
)
from app.ops.notifications import ReminderMessage, get_notification_provider
from app.safeguarding_alerts import access, ai_support, rules
from app.safeguarding_alerts.constants import (
    ALERT_PRIORITIES,
    DEFAULT_CATEGORIES,
    PUSH_PREVIEW_SAFE,
    STATUS_TRANSITIONS,
)
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _settings_row(session: Session, org_id: UUID) -> OrganisationSafeguardingAlertSettings:
    row = session.scalars(
        select(OrganisationSafeguardingAlertSettings).where(
            OrganisationSafeguardingAlertSettings.organisation_id == org_id
        )
    ).first()
    if row is None:
        row = OrganisationSafeguardingAlertSettings(
            organisation_id=org_id,
            emergency_guidance_text=(
                "This service is not an emergency line. If you or someone else is in immediate danger, "
                "contact the emergency services (999) or your organisation's approved emergency contact."
            ),
        )
        session.add(row)
        session.flush()
    return row


def assert_addon_available(session: Session, settings: Settings, org_id: UUID) -> OrganisationSafeguardingAlertSettings:
    if not settings.safeguarding_alerts_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Safeguarding alerts add-on is not enabled platform-wide")
    row = _settings_row(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Safeguarding alerts disabled for this organisation")
    if not row.privacy_review_complete and row.enabled:
        pass  # operational with privacy review flagged in admin UI
    return row


def settings_to_dict(row: OrganisationSafeguardingAlertSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "retention_days": row.retention_days,
        "ai_assist_enabled": row.ai_assist_enabled,
        "default_notification_channel": row.default_notification_channel,
        "escalation_targets": row.escalation_targets,
        "emergency_guidance_text": row.emergency_guidance_text,
    }


def ensure_default_categories(session: Session, org_id: UUID) -> None:
    existing = session.scalar(
        select(func.count()).select_from(SafeguardingAlertCategory).where(SafeguardingAlertCategory.organisation_id == org_id)
    )
    if existing and existing > 0:
        return
    for idx, (slug, name, desc) in enumerate(DEFAULT_CATEGORIES):
        session.add(
            SafeguardingAlertCategory(
                organisation_id=org_id,
                slug=slug,
                name=name,
                description=desc,
                is_system=True,
                sort_order=idx,
            )
        )
    session.flush()


def seed_default_rules(session: Session, org_id: UUID) -> None:
    """Idempotent default rules when categories exist."""
    ensure_default_categories(session, org_id)
    count = session.scalar(
        select(func.count()).select_from(SafeguardingAlertRule).where(SafeguardingAlertRule.organisation_id == org_id)
    )
    if count and count > 0:
        return
    cats = {
        c.slug: c for c in session.scalars(
            select(SafeguardingAlertCategory).where(SafeguardingAlertCategory.organisation_id == org_id)
        ).all()
    }
    templates = [
        ("Repeated missed appointments", "repeated_missed_appointments", "missed_appointments", "medium"),
        ("Multiple unresolved tasks", "multiple_unresolved_support_tasks", "welfare_concerns", "medium"),
        ("Repeated incidents", "repeated_reported_incidents", "reported_incidents", "high"),
        ("Overdue safeguarding follow-ups", "overdue_safeguarding_followups", "staff_reported", "high"),
        ("Repeated welfare alerts", "repeated_welfare_concerns", "welfare_concerns", "medium"),
        ("Urgent maintenance open", "unresolved_urgent_maintenance", "maintenance_safety", "high"),
        ("Support plan review overdue", "support_plan_review_failures", "welfare_concerns", "medium"),
    ]
    for name, trigger, cat_slug, priority in templates:
        cat = cats.get(cat_slug)
        if cat is None:
            continue
        session.add(
            SafeguardingAlertRule(
                organisation_id=org_id,
                name=name,
                description=f"Configurable early-warning rule: {name}. Human review required.",
                trigger_type=trigger,
                trigger_config={"window_days": 30, "threshold": 2},
                category_id=cat.id,
                priority=priority,
                responsible_team="support",
                notification_method="in_app",
                enabled=False,
            )
        )
    session.flush()


def update_settings(session: Session, ctx: OrganisationContext, payload: dict[str, Any]) -> dict[str, Any]:
    row = _settings_row(session, ctx.organisation_id)
    for key in (
        "enabled",
        "privacy_review_complete",
        "retention_days",
        "ai_assist_enabled",
        "default_notification_channel",
        "escalation_targets",
        "emergency_guidance_text",
    ):
        if key in payload and payload[key] is not None:
            setattr(row, key, payload[key])
    if row.enabled:
        ensure_default_categories(session, ctx.organisation_id)
        seed_default_rules(session, ctx.organisation_id)
    session.flush()
    record_event(
        session,
        action=audit_events.SAFEGUARDING_ALERTS_SETTINGS_UPDATE,
        resource_type="safeguarding_alert_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Safeguarding alert settings updated",
        metadata={"enabled": row.enabled},
    )
    return settings_to_dict(row)


def _next_ref(session: Session, org_id: UUID, prefix: str) -> str:
    year = _now().year
    full = f"{prefix}-{year}-"
    count = (
        session.scalar(
            select(func.count())
            .select_from(SafeguardingAlert)
            .where(SafeguardingAlert.organisation_id == org_id, SafeguardingAlert.reference_number.like(f"{full}%"))
        )
        or 0
    )
    return f"{full}{count + 1:05d}"


def _record_status(
    session: Session,
    ctx: OrganisationContext,
    alert: SafeguardingAlert,
    *,
    from_status: str | None,
    to_status: str,
    notes: str | None = None,
) -> None:
    session.add(
        SafeguardingAlertStatusHistory(
            organisation_id=ctx.organisation_id,
            alert_id=alert.id,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value if ctx.role else None,
            notes=notes,
        )
    )


def _notify_user(
    session: Session,
    *,
    organisation_id: UUID,
    user_id: UUID,
    alert: SafeguardingAlert,
    channel: str,
    subject: str,
) -> None:
    body = PUSH_PREVIEW_SAFE if channel == "push" else f"Alert {alert.reference_number}: review required."
    provider = get_notification_provider()
    provider.send(
        session,
        ReminderMessage(
            organisation_id=str(organisation_id),
            recipient_user_id=str(user_id),
            subject=subject[:500],
            body=body,
            channel=channel,
            target_type="safeguarding_alert",
            target_id=str(alert.id),
            idempotency_key=f"safeguarding-alert:{alert.id}:{user_id}:{channel}:{subject[:40]}",
            essential_operational=True,
        ),
    )


def alert_to_dict(alert: SafeguardingAlert, *, category_slug: str | None = None) -> dict[str, Any]:
    return {
        "id": str(alert.id),
        "reference_number": alert.reference_number,
        "organisation_id": str(alert.organisation_id),
        "tenant_id": str(alert.tenant_id) if alert.tenant_id else None,
        "category_id": str(alert.category_id),
        "category_slug": category_slug,
        "rule_id": str(alert.rule_id) if alert.rule_id else None,
        "description": alert.description,
        "source": alert.source,
        "source_type": alert.source_type,
        "status": alert.status,
        "priority": alert.priority,
        "assigned_user_id": str(alert.assigned_user_id) if alert.assigned_user_id else None,
        "follow_up_at": alert.follow_up_at.isoformat() if alert.follow_up_at else None,
        "resolution_notes": alert.resolution_notes,
        "closed_at": alert.closed_at.isoformat() if alert.closed_at else None,
        "requires_human_review": alert.requires_human_review,
        "alert_metadata": alert.alert_metadata,
        "created_at": alert.created_at.isoformat(),
        "updated_at": alert.updated_at.isoformat(),
    }


def create_alert(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: UUID | None,
    category_id: UUID,
    description: str,
    priority: str = "medium",
    source: str = "staff",
    source_type: str = "manual",
    rule_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    follow_up_at: datetime | None = None,
    requires_human_review: bool = False,
    dedupe_key: str | None = None,
    alert_metadata: dict[str, Any] | None = None,
) -> SafeguardingAlert:
    assert_addon_available(session, get_settings(), ctx.organisation_id)
    if priority not in ALERT_PRIORITIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid priority")
    if dedupe_key:
        existing = session.scalar(
            select(SafeguardingAlert).where(
                SafeguardingAlert.organisation_id == ctx.organisation_id,
                SafeguardingAlert.dedupe_key == dedupe_key,
            )
        )
        if existing is not None:
            return existing
    alert = SafeguardingAlert(
        organisation_id=ctx.organisation_id,
        reference_number=_next_ref(session, ctx.organisation_id, "SGA"),
        tenant_id=tenant_id,
        category_id=category_id,
        rule_id=rule_id,
        description=description,
        source=source,
        source_type=source_type,
        status="new",
        priority=priority,
        assigned_user_id=assigned_user_id,
        follow_up_at=follow_up_at,
        requires_human_review=requires_human_review or source_type in {"rule", "ai_suggestion"},
        dedupe_key=dedupe_key,
        alert_metadata=alert_metadata or {},
    )
    session.add(alert)
    session.flush()
    _record_status(session, ctx, alert, from_status=None, to_status="new", notes="Alert created")
    record_event(
        session,
        action=audit_events.SAFEGUARDING_ALERT_CREATED,
        resource_type="safeguarding_alert",
        resource_id=str(alert.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Safeguarding alert created",
        metadata={"source_type": source_type, "priority": priority},
    )
    settings = _settings_row(session, ctx.organisation_id)
    if assigned_user_id:
        _notify_user(
            session,
            organisation_id=ctx.organisation_id,
            user_id=assigned_user_id,
            alert=alert,
            channel=settings.default_notification_channel,
            subject="Safeguarding alert assigned",
        )
    return alert


def transition_status(
    session: Session,
    ctx: OrganisationContext,
    alert: SafeguardingAlert,
    new_status: str,
    *,
    notes: str | None = None,
) -> SafeguardingAlert:
    allowed = STATUS_TRANSITIONS.get(alert.status, frozenset())
    if new_status not in allowed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Cannot transition {alert.status} -> {new_status}")
    prev = alert.status
    alert.status = new_status
    if new_status == "closed":
        alert.closed_at = _now()
    session.flush()
    _record_status(session, ctx, alert, from_status=prev, to_status=new_status, notes=notes)
    record_event(
        session,
        action=audit_events.SAFEGUARDING_ALERT_STATUS_CHANGE,
        resource_type="safeguarding_alert",
        resource_id=str(alert.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Safeguarding alert status updated",
        metadata={"from": prev, "to": new_status},
    )
    return alert


def list_alerts(
    session: Session,
    ctx: OrganisationContext,
    *,
    status: str | None = None,
    priority: str | None = None,
    category_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
) -> list[dict[str, Any]]:
    q = select(SafeguardingAlert, SafeguardingAlertCategory.slug).join(
        SafeguardingAlertCategory, SafeguardingAlertCategory.id == SafeguardingAlert.category_id
    ).where(SafeguardingAlert.organisation_id == ctx.organisation_id)
    if status:
        q = q.where(SafeguardingAlert.status == status)
    if priority:
        q = q.where(SafeguardingAlert.priority == priority)
    if category_id:
        q = q.where(SafeguardingAlert.category_id == category_id)
    if assigned_user_id:
        q = q.where(SafeguardingAlert.assigned_user_id == assigned_user_id)
    rows = session.execute(q.order_by(SafeguardingAlert.created_at.desc()).limit(200)).all()
    out: list[dict[str, Any]] = []
    for alert, slug in rows:
        access.assert_alert_visible(session, ctx, alert, category_slug=slug)
        out.append(alert_to_dict(alert, category_slug=slug))
    return out


def dashboard_stats(session: Session, org_id: UUID) -> dict[str, Any]:
    total = (
        session.scalar(
            select(func.count()).select_from(SafeguardingAlert).where(SafeguardingAlert.organisation_id == org_id)
        )
        or 0
    )
    by_status: dict[str, int] = {}
    for st in ("new", "under_review", "assigned", "action_required", "escalated", "resolved", "closed"):
        by_status[st] = int(
            session.scalar(
                select(func.count()).select_from(SafeguardingAlert).where(
                    SafeguardingAlert.organisation_id == org_id, SafeguardingAlert.status == st
                )
            )
            or 0
        )
    overdue = int(
        session.scalar(
            select(func.count()).select_from(SafeguardingAlert).where(
                SafeguardingAlert.organisation_id == org_id,
                SafeguardingAlert.follow_up_at.is_not(None),
                SafeguardingAlert.follow_up_at < _now(),
                SafeguardingAlert.status.notin_(("resolved", "closed")),
            )
        )
        or 0
    )
    critical = int(
        session.scalar(
            select(func.count()).select_from(SafeguardingAlert).where(
                SafeguardingAlert.organisation_id == org_id,
                SafeguardingAlert.priority == "critical",
                SafeguardingAlert.status.notin_(("resolved", "closed")),
            )
        )
        or 0
    )
    return {"total_alerts": int(total), "by_status": by_status, "overdue_follow_ups": overdue, "critical_open": critical}


def run_rules(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    assert_addon_available(session, get_settings(), ctx.organisation_id)
    hits = rules.evaluate_all_rules(session, ctx.organisation_id)
    created = 0
    for hit in hits:
        create_alert(
            session,
            ctx,
            tenant_id=hit.tenant_id,
            category_id=hit.rule.category_id,
            description=hit.description,
            priority=hit.rule.priority,
            source="rule_engine",
            source_type="rule",
            rule_id=hit.rule.id,
            requires_human_review=True,
            dedupe_key=hit.dedupe_key,
            alert_metadata=hit.metadata,
        )
        created += 1
    record_event(
        session,
        action=audit_events.SAFEGUARDING_ALERT_RULES_EVALUATED,
        resource_type="safeguarding_alert_rules",
        resource_id=str(ctx.organisation_id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Safeguarding rules evaluated",
        metadata={"hits": len(hits), "alerts_recorded": created},
    )
    return {"hits": len(hits), "alerts_recorded": created}


def escalate_alert(
    session: Session,
    ctx: OrganisationContext,
    alert: SafeguardingAlert,
    *,
    target_role: str,
    target_user_id: UUID | None,
    reason: str | None,
) -> SafeguardingAlertEscalation:
    access.require_escalate(ctx)
    level = (
        session.scalar(
            select(func.max(SafeguardingAlertEscalation.escalation_level)).where(
                SafeguardingAlertEscalation.alert_id == alert.id
            )
        )
        or 0
    ) + 1
    esc = SafeguardingAlertEscalation(
        organisation_id=ctx.organisation_id,
        alert_id=alert.id,
        escalation_level=int(level),
        target_role=target_role,
        target_user_id=target_user_id,
        reason=reason,
    )
    session.add(esc)
    transition_status(session, ctx, alert, "escalated", notes=reason)
    record_event(
        session,
        action=audit_events.SAFEGUARDING_ALERT_ESCALATED,
        resource_type="safeguarding_alert",
        resource_id=str(alert.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Safeguarding alert escalated",
        metadata={"level": level, "target_role": target_role},
    )
    settings = _settings_row(session, ctx.organisation_id)
    if target_user_id:
        _notify_user(
            session,
            organisation_id=ctx.organisation_id,
            user_id=target_user_id,
            alert=alert,
            channel=settings.default_notification_channel,
            subject="Safeguarding escalation",
        )
    return esc


def add_review(
    session: Session,
    ctx: OrganisationContext,
    alert: SafeguardingAlert,
    *,
    review_type: str,
    content: str,
    evidence_refs: list | None,
    approved: bool,
) -> SafeguardingAlertReview:
    access.require_review_assigned(ctx)
    review = SafeguardingAlertReview(
        organisation_id=ctx.organisation_id,
        alert_id=alert.id,
        review_type=review_type,
        content=content,
        evidence_refs=evidence_refs or [],
        approved=approved,
        reviewer_user_id=ctx.user_id,
    )
    session.add(review)
    session.flush()
    if review_type == "acknowledgement" and alert.status == "new":
        transition_status(session, ctx, alert, "under_review")
    record_event(
        session,
        action=audit_events.SAFEGUARDING_ALERT_REVIEW_RECORDED,
        resource_type="safeguarding_alert",
        resource_id=str(alert.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Safeguarding review recorded",
        metadata={"review_type": review_type, "approved": approved},
    )
    return review


def close_alert(
    session: Session,
    ctx: OrganisationContext,
    alert: SafeguardingAlert,
    *,
    resolution_notes: str,
    supervisor_approved: bool,
) -> SafeguardingAlert:
    if not supervisor_approved and ctx.role not in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Closure requires supervisor approval")
    alert.resolution_notes = resolution_notes
    transition_status(session, ctx, alert, "resolved", notes=resolution_notes)
    transition_status(session, ctx, alert, "closed", notes="Closure approved")
    record_event(
        session,
        action=audit_events.SAFEGUARDING_ALERT_CLOSED,
        resource_type="safeguarding_alert",
        resource_id=str(alert.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Safeguarding alert closed",
    )
    return alert


def submit_tenant_report(
    session: Session,
    ctx: OrganisationContext,
    *,
    category_id: UUID,
    description: str,
    attachment_file_id: UUID | None,
) -> dict[str, Any]:
    access.require_tenant_report(ctx)
    assert_addon_available(session, get_settings(), ctx.organisation_id)
    tenant_id = access.resolve_tenant_for_user(session, ctx)
    settings = _settings_row(session, ctx.organisation_id)
    ref_year = _now().year
    tr_count = (
        session.scalar(
            select(func.count()).select_from(SafeguardingTenantReport).where(
                SafeguardingTenantReport.organisation_id == ctx.organisation_id,
                SafeguardingTenantReport.reference_number.like(f"SGR-{ref_year}-%"),
            )
        )
        or 0
    )
    ref = f"SGR-{ref_year}-{tr_count + 1:05d}"
    report = SafeguardingTenantReport(
        organisation_id=ctx.organisation_id,
        reference_number=ref,
        reporter_user_id=ctx.user_id,
        tenant_id=tenant_id,
        category_id=category_id,
        description=description,
        attachment_file_id=attachment_file_id,
        status="received",
    )
    session.add(report)
    session.flush()
    alert = create_alert(
        session,
        ctx,
        tenant_id=tenant_id,
        category_id=category_id,
        description=f"Tenant report {ref}: {description[:500]}",
        priority="medium",
        source="tenant_app",
        source_type="tenant_report",
        requires_human_review=True,
        dedupe_key=f"tenant-report:{report.id}",
        alert_metadata={"tenant_report_id": str(report.id)},
    )
    report.alert_id = alert.id
    report.status = "linked"
    session.flush()
    record_event(
        session,
        action=audit_events.SAFEGUARDING_TENANT_REPORT_SUBMITTED,
        resource_type="safeguarding_tenant_report",
        resource_id=str(report.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Tenant safeguarding report submitted",
    )
    return {
        "reference_number": ref,
        "alert_id": str(alert.id),
        "emergency_guidance": settings.emergency_guidance_text,
        "message": "Your concern has been received for human review. This is not an emergency service.",
    }


def run_ai_assist(
    session: Session,
    ctx: OrganisationContext,
    *,
    alert_id: UUID | None,
    tenant_id: UUID,
) -> dict[str, Any]:
    row = _settings_row(session, ctx.organisation_id)
    if not row.ai_assist_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="AI assist disabled for organisation")
    draft = ai_support.build_case_summary_draft(session, organisation_id=ctx.organisation_id, tenant_id=tenant_id)
    suggestion = SafeguardingAlertAiSuggestion(
        organisation_id=ctx.organisation_id,
        alert_id=alert_id,
        tenant_id=tenant_id,
        suggestion_type=draft["suggestion_type"],
        content=draft["content"],
        source_refs=draft["source_refs"],
        uncertainty_note=draft["uncertainty_note"],
        requires_human_review=True,
        human_approved=False,
        ai_request_id=str(uuid.uuid4()),
    )
    session.add(suggestion)
    session.flush()
    record_and_reconcile(
        session,
        request_id=str(suggestion.ai_request_id),
        organisation_id=ctx.organisation_id,
        execution_status="completed",
        feature_id=ai_features.FEATURE_SAFEGUARDING_ALERTS,
        workflow_id="safeguarding_ai_assist",
        user_id=ctx.user_id,
        provider="local",
        model_id="safeguarding-assist-organiser",
        input_tokens=0,
        output_tokens=len(draft["content"].split()),
        metadata={"suggestion_id": str(suggestion.id)},
    )
    record_event(
        session,
        action=audit_events.SAFEGUARDING_ALERT_AI_SUGGESTION,
        resource_type="safeguarding_alert_ai_suggestion",
        resource_id=str(suggestion.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="AI safeguarding suggestion recorded",
    )
    return {
        "id": str(suggestion.id),
        "requires_human_review": True,
        "uncertainty_note": draft["uncertainty_note"],
        "content": draft["content"],
        "source_refs": draft["source_refs"],
    }


def approve_ai_suggestion(session: Session, ctx: OrganisationContext, suggestion_id: UUID) -> dict[str, Any]:
    suggestion = session.get(SafeguardingAlertAiSuggestion, suggestion_id)
    if suggestion is None or suggestion.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
    suggestion.human_approved = True
    session.flush()
    if suggestion.alert_id is None and suggestion.tenant_id is not None:
        cat = session.scalar(
            select(SafeguardingAlertCategory).where(
                SafeguardingAlertCategory.organisation_id == ctx.organisation_id,
                SafeguardingAlertCategory.slug == "other",
            )
        )
        if cat:
            create_alert(
                session,
                ctx,
                tenant_id=suggestion.tenant_id,
                category_id=cat.id,
                description=f"Human-approved AI draft:\n{suggestion.content[:2000]}",
                priority="low",
                source="ai_assist",
                source_type="ai_suggestion",
                requires_human_review=True,
                dedupe_key=f"ai-suggestion:{suggestion.id}",
                alert_metadata={"ai_suggestion_id": str(suggestion.id)},
            )
    record_event(
        session,
        action=audit_events.SAFEGUARDING_ALERT_AI_APPROVED,
        resource_type="safeguarding_alert_ai_suggestion",
        resource_id=str(suggestion.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="AI safeguarding suggestion approved by human",
    )
    return {"id": str(suggestion.id), "human_approved": True}


def process_overdue_escalations(session: Session, organisation_id: UUID) -> int:
    """Escalate overdue open alerts using organisation escalation_targets — no fixed SLA."""
    settings = _settings_row(session, organisation_id)
    if not settings.enabled:
        return 0
    targets = settings.escalation_targets or {}
    target_role = targets.get("overdue_role", "organisation_admin")
    alerts = session.scalars(
        select(SafeguardingAlert).where(
            SafeguardingAlert.organisation_id == organisation_id,
            SafeguardingAlert.follow_up_at.is_not(None),
            SafeguardingAlert.follow_up_at < _now(),
            SafeguardingAlert.status.notin_(("resolved", "closed", "escalated")),
        )
    ).all()
    count = 0
    for alert in alerts:
        esc = SafeguardingAlertEscalation(
            organisation_id=organisation_id,
            alert_id=alert.id,
            escalation_level=1,
            target_role=str(target_role),
            reason="Overdue follow-up (organisation rule)",
        )
        session.add(esc)
        prev = alert.status
        alert.status = "escalated"
        session.add(
            SafeguardingAlertStatusHistory(
                organisation_id=organisation_id,
                alert_id=alert.id,
                from_status=prev,
                to_status="escalated",
                notes="Automatic overdue escalation",
            )
        )
        count += 1
    session.flush()
    return count
