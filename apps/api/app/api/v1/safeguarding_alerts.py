"""F8.2 optional advanced safeguarding alerts API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.safeguarding_alerts import (
    SafeguardingAlert,
    SafeguardingAlertCategory,
    SafeguardingAlertRule,
)
from app.db.session import get_session
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.safeguarding_alerts import access, service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/safeguarding-alerts", tags=["safeguarding-alerts"])


class SettingsBody(BaseModel):
    enabled: bool | None = None
    privacy_review_complete: bool | None = None
    retention_days: int | None = Field(default=None, ge=30, le=3650)
    ai_assist_enabled: bool | None = None
    default_notification_channel: str | None = None
    escalation_targets: dict[str, Any] | None = None
    emergency_guidance_text: str | None = None


class CategoryBody(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    active: bool | None = None


class RuleBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    trigger_type: str
    trigger_config: dict[str, Any] | None = None
    category_id: uuid.UUID
    priority: str = "medium"
    responsible_team: str = "support"
    notification_method: str = "in_app"
    enabled: bool | None = True


class AlertCreateBody(BaseModel):
    tenant_id: uuid.UUID | None = None
    category_id: uuid.UUID
    description: str = Field(min_length=1, max_length=8000)
    priority: str = "medium"
    assigned_user_id: uuid.UUID | None = None
    follow_up_at: datetime | None = None


class StatusBody(BaseModel):
    status: str
    notes: str | None = None


class ReviewBody(BaseModel):
    review_type: str
    content: str = Field(min_length=1, max_length=8000)
    evidence_refs: list[dict[str, Any]] | None = None
    approved: bool = False


class EscalateBody(BaseModel):
    target_role: str
    target_user_id: uuid.UUID | None = None
    reason: str | None = None


class CloseBody(BaseModel):
    resolution_notes: str = Field(min_length=1, max_length=8000)
    supervisor_approved: bool = False


class TenantReportBody(BaseModel):
    category_id: uuid.UUID
    description: str = Field(min_length=1, max_length=4000)
    attachment_file_id: uuid.UUID | None = None


class AiAssistBody(BaseModel):
    tenant_id: uuid.UUID
    alert_id: uuid.UUID | None = None


@router.get("/settings")
def get_settings(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_READ)
    from app.safeguarding_alerts.service import _settings_row, settings_to_dict

    return settings_to_dict(_settings_row(session, ctx.organisation_id))


@router.patch("/settings")
def patch_settings(
    body: SettingsBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_MANAGE)
    return service.update_settings(session, ctx, body.model_dump(exclude_unset=True))


@router.get("/dashboard")
def dashboard(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    access.require_addon_read(ctx)
    return service.dashboard_stats(session, ctx.organisation_id)


@router.get("/categories")
def list_categories(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> list[dict[str, Any]]:
    access.require_addon_read(ctx)
    service.ensure_default_categories(session, ctx.organisation_id)
    rows = session.scalars(
        select(SafeguardingAlertCategory)
        .where(SafeguardingAlertCategory.organisation_id == ctx.organisation_id)
        .order_by(SafeguardingAlertCategory.sort_order)
    ).all()
    return [
        {
            "id": str(r.id),
            "slug": r.slug,
            "name": r.name,
            "description": r.description,
            "active": r.active,
            "is_system": r.is_system,
        }
        for r in rows
    ]


@router.get("/rules")
def list_rules(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_RULES_MANAGE)
    rows = session.scalars(
        select(SafeguardingAlertRule).where(SafeguardingAlertRule.organisation_id == ctx.organisation_id)
    ).all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "trigger_type": r.trigger_type,
            "trigger_config": r.trigger_config,
            "category_id": str(r.category_id),
            "priority": r.priority,
            "responsible_team": r.responsible_team,
            "notification_method": r.notification_method,
            "enabled": r.enabled,
        }
        for r in rows
    ]


@router.post("/rules")
def create_rule(
    body: RuleBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    access.require_rules_manage(ctx)
    rule = SafeguardingAlertRule(
        organisation_id=ctx.organisation_id,
        name=body.name,
        description=body.description,
        trigger_type=body.trigger_type,
        trigger_config=body.trigger_config or {},
        category_id=body.category_id,
        priority=body.priority,
        responsible_team=body.responsible_team,
        notification_method=body.notification_method,
        enabled=bool(body.enabled),
    )
    session.add(rule)
    session.flush()
    return {"id": str(rule.id)}


@router.post("/rules/evaluate")
def evaluate_rules(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    access.require_rules_manage(ctx)
    return service.run_rules(session, ctx)


@router.get("/alerts")
def list_alerts(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    category_id: uuid.UUID | None = Query(default=None),
    assigned_user_id: uuid.UUID | None = Query(default=None),
) -> list[dict[str, Any]]:
    access.require_addon_read(ctx)
    return service.list_alerts(
        session,
        ctx,
        status=status,
        priority=priority,
        category_id=category_id,
        assigned_user_id=assigned_user_id,
    )


@router.post("/alerts")
def create_alert_endpoint(
    body: AlertCreateBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_MANAGE)
    alert = service.create_alert(
        session,
        ctx,
        tenant_id=body.tenant_id,
        category_id=body.category_id,
        description=body.description,
        priority=body.priority,
        assigned_user_id=body.assigned_user_id,
        follow_up_at=body.follow_up_at,
    )
    return service.alert_to_dict(alert)


@router.get("/alerts/{alert_id}")
def get_alert(
    alert_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    access.require_addon_read(ctx)
    row = session.execute(
        select(SafeguardingAlert, SafeguardingAlertCategory.slug)
        .join(SafeguardingAlertCategory, SafeguardingAlertCategory.id == SafeguardingAlert.category_id)
        .where(SafeguardingAlert.id == alert_id, SafeguardingAlert.organisation_id == ctx.organisation_id)
    ).first()
    if row is None:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert, slug = row
    access.assert_alert_visible(session, ctx, alert, category_slug=slug)
    return service.alert_to_dict(alert, category_slug=slug)


@router.post("/alerts/{alert_id}/status")
def update_status(
    alert_id: uuid.UUID,
    body: StatusBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    access.require_review_assigned(ctx)
    alert = session.get(SafeguardingAlert, alert_id)
    if alert is None or alert.organisation_id != ctx.organisation_id:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert = service.transition_status(session, ctx, alert, body.status, notes=body.notes)
    return service.alert_to_dict(alert)


@router.post("/alerts/{alert_id}/reviews")
def add_review(
    alert_id: uuid.UUID,
    body: ReviewBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    alert = session.get(SafeguardingAlert, alert_id)
    if alert is None or alert.organisation_id != ctx.organisation_id:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert not found")
    review = service.add_review(
        session,
        ctx,
        alert,
        review_type=body.review_type,
        content=body.content,
        evidence_refs=body.evidence_refs,
        approved=body.approved,
    )
    return {"id": str(review.id), "review_type": review.review_type, "approved": review.approved}


@router.post("/alerts/{alert_id}/escalate")
def escalate(
    alert_id: uuid.UUID,
    body: EscalateBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    alert = session.get(SafeguardingAlert, alert_id)
    if alert is None or alert.organisation_id != ctx.organisation_id:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert not found")
    esc = service.escalate_alert(
        session,
        ctx,
        alert,
        target_role=body.target_role,
        target_user_id=body.target_user_id,
        reason=body.reason,
    )
    return {"id": str(esc.id), "escalation_level": esc.escalation_level}


@router.post("/alerts/{alert_id}/close")
def close_alert(
    alert_id: uuid.UUID,
    body: CloseBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    alert = session.get(SafeguardingAlert, alert_id)
    if alert is None or alert.organisation_id != ctx.organisation_id:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert = service.close_alert(
        session,
        ctx,
        alert,
        resolution_notes=body.resolution_notes,
        supervisor_approved=body.supervisor_approved,
    )
    return service.alert_to_dict(alert)


@router.post("/tenant-reports")
def tenant_report(
    body: TenantReportBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    return service.submit_tenant_report(
        session,
        ctx,
        category_id=body.category_id,
        description=body.description,
        attachment_file_id=body.attachment_file_id,
    )


@router.post("/ai-assist")
def ai_assist(
    body: AiAssistBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_MANAGE)
    return service.run_ai_assist(session, ctx, alert_id=body.alert_id, tenant_id=body.tenant_id)


@router.post("/ai-suggestions/{suggestion_id}/approve")
def approve_ai(
    suggestion_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_MANAGE)
    return service.approve_ai_suggestion(session, ctx, suggestion_id)


@router.get("/reports/summary")
def report_summary(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_MANAGE)
    return service.dashboard_stats(session, ctx.organisation_id)
