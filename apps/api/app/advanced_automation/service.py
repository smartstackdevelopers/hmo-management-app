"""F8.11 advanced automation — intelligent workflows on F6.3 + F2.13."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.advanced_automation.ai_client import suggest_workflow
from app.advanced_automation.constants import (
    ADDON_DISCLAIMER,
    AI_NOTICE,
    WORKFLOW_TEMPLATES,
    WORKFLOW_TRIGGERS,
)
from app.advanced_automation.validation import validate_conditions, validate_steps
from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.automation import service as automation_service
from app.core.config import Settings, get_settings
from app.db.models.intelligent_workflows import (
    IntelligentWorkflow,
    IntelligentWorkflowApproval,
    IntelligentWorkflowAuditLog,
    IntelligentWorkflowExecution,
    IntelligentWorkflowNotificationLog,
    IntelligentWorkflowNotificationTemplate,
    IntelligentWorkflowScheduledTask,
    IntelligentWorkflowVersion,
    OrganisationAdvancedAutomationSettings,
)
from app.org_workflows import dashboard as org_workflow_dashboard
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _settings(session: Session, org_id: UUID) -> OrganisationAdvancedAutomationSettings:
    row = session.scalars(
        select(OrganisationAdvancedAutomationSettings).where(
            OrganisationAdvancedAutomationSettings.organisation_id == org_id
        )
    ).first()
    if row is None:
        row = OrganisationAdvancedAutomationSettings(organisation_id=org_id)
        session.add(row)
        session.flush()
    return row


def assert_addon(session: Session, settings: Settings, org_id: UUID) -> OrganisationAdvancedAutomationSettings:
    if not settings.advanced_automation_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Advanced automation add-on disabled platform-wide")
    row = _settings(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Advanced automation disabled for organisation")
    return row


def settings_dict(row: OrganisationAdvancedAutomationSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "ai_assistant_enabled": row.ai_assistant_enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "notification_prefs": row.notification_prefs,
        "disclaimer": ADDON_DISCLAIMER,
    }


def update_settings(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> OrganisationAdvancedAutomationSettings:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_MANAGE)
    row = assert_addon(session, get_settings(), ctx.organisation_id)
    for key in ("enabled", "ai_assistant_enabled", "privacy_review_complete"):
        if data.get(key) is not None:
            setattr(row, key, bool(data[key]))
    if data.get("notification_prefs") is not None:
        row.notification_prefs = data["notification_prefs"]
    session.flush()
    record_event(
        session,
        action=audit_events.ADVANCED_AUTOMATION_SETTINGS_UPDATE,
        resource_type="advanced_automation_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Advanced automation settings updated",
    )
    return row


def _audit(session: Session, ctx: OrganisationContext, workflow_id: UUID | None, action: str, summary: str) -> None:
    session.add(
        IntelligentWorkflowAuditLog(
            organisation_id=ctx.organisation_id,
            workflow_id=workflow_id,
            action=action,
            actor_user_id=ctx.user_id,
            summary=summary[:2000],
        )
    )


def deep_dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_READ)
    assert_addon(session, get_settings(), ctx.organisation_id)
    org = ctx.organisation_id
    total = session.scalar(select(func.count()).select_from(IntelligentWorkflow).where(IntelligentWorkflow.organisation_id == org)) or 0
    active = (
        session.scalar(
            select(func.count()).select_from(IntelligentWorkflow).where(
                IntelligentWorkflow.organisation_id == org, IntelligentWorkflow.status == "active"
            )
        )
        or 0
    )
    draft = (
        session.scalar(
            select(func.count()).select_from(IntelligentWorkflow).where(
                IntelligentWorkflow.organisation_id == org, IntelligentWorkflow.status == "draft"
            )
        )
        or 0
    )
    running = (
        session.scalar(
            select(func.count()).select_from(IntelligentWorkflowExecution).where(
                IntelligentWorkflowExecution.organisation_id == org,
                IntelligentWorkflowExecution.status == "running",
            )
        )
        or 0
    )
    completed = (
        session.scalar(
            select(func.count()).select_from(IntelligentWorkflowExecution).where(
                IntelligentWorkflowExecution.organisation_id == org,
                IntelligentWorkflowExecution.status == "completed",
            )
        )
        or 0
    )
    failed = (
        session.scalar(
            select(func.count()).select_from(IntelligentWorkflowExecution).where(
                IntelligentWorkflowExecution.organisation_id == org,
                IntelligentWorkflowExecution.status == "failed",
            )
        )
        or 0
    )
    pending_approvals = (
        session.scalar(
            select(func.count()).select_from(IntelligentWorkflowApproval).where(
                IntelligentWorkflowApproval.organisation_id == org,
                IntelligentWorkflowApproval.status == "pending",
            )
        )
        or 0
    )
    avg_seconds: float | None = None
    rows = session.scalars(
        select(IntelligentWorkflowExecution).where(
            IntelligentWorkflowExecution.organisation_id == org,
            IntelligentWorkflowExecution.status == "completed",
            IntelligentWorkflowExecution.started_at.isnot(None),
            IntelligentWorkflowExecution.completed_at.isnot(None),
        )
    ).all()
    if rows:
        deltas = [(r.completed_at - r.started_at).total_seconds() for r in rows if r.completed_at and r.started_at]
        if deltas:
            avg_seconds = sum(deltas) / len(deltas)
    success_rate: float | None = None
    done_total = completed + failed
    if done_total:
        success_rate = round(100.0 * completed / done_total, 2)
    auto_base = {}
    try:
        auto_base = automation_service.dashboard(session, ctx)
    except Exception:
        auto_base = {}
    org_inbox = {}
    try:
        org_inbox = org_workflow_dashboard.dashboard(session, ctx)
    except Exception:
        org_inbox = {}
    return {
        **auto_base,
        "intelligent_workflows_total": int(total),
        "intelligent_workflows_active": int(active),
        "intelligent_workflows_draft": int(draft),
        "executions_running": int(running),
        "executions_completed": int(completed),
        "executions_failed": int(failed),
        "pending_approvals": int(pending_approvals),
        "org_approval_inbox_pending": org_inbox.get("pending_approvals", 0),
        "avg_completion_seconds": avg_seconds,
        "automation_success_rate_percent": success_rate,
        "disclaimer": ADDON_DISCLAIMER,
    }


def list_templates(ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_READ)
    return [{"key": k, "name": n, "steps": steps} for k, n, steps in WORKFLOW_TEMPLATES]


def list_triggers(ctx: OrganisationContext) -> list[dict[str, str]]:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_READ)
    return [{"slug": s, "label": label} for s, label in WORKFLOW_TRIGGERS]


def create_workflow(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> IntelligentWorkflow:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_MANAGE)
    assert_addon(session, get_settings(), ctx.organisation_id)
    slug = data["slug"].strip().lower()
    row = IntelligentWorkflow(
        organisation_id=ctx.organisation_id,
        slug=slug,
        name=data["name"],
        description=data.get("description"),
        status="draft",
        template_key=data.get("template_key"),
        created_by_user_id=ctx.user_id,
    )
    session.add(row)
    session.flush()
    version = IntelligentWorkflowVersion(
        organisation_id=ctx.organisation_id,
        workflow_id=row.id,
        version_number=1,
        steps_json=data.get("steps") or [],
        triggers_json=data.get("triggers") or [],
        conditions_json=data.get("conditions") or {},
        editor_user_id=ctx.user_id,
    )
    session.add(version)
    session.flush()
    row.active_version_id = version.id
    _audit(session, ctx, row.id, "workflow.created", f"Created workflow {row.name}")
    session.flush()
    record_event(
        session,
        action=audit_events.ADVANCED_AUTOMATION_WORKFLOW_CREATED,
        resource_type="intelligent_workflow",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Intelligent workflow created: {row.name}",
    )
    return row


def save_draft_version(session: Session, ctx: OrganisationContext, workflow_id: UUID, data: dict[str, Any]) -> IntelligentWorkflowVersion:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_MANAGE)
    wf = session.get(IntelligentWorkflow, workflow_id)
    if wf is None or wf.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    if wf.status == "active" and not data.get("create_new_version"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Active workflow requires create_new_version to edit")
    steps = data.get("steps")
    conditions = data.get("conditions")
    triggers = data.get("triggers")
    if steps is not None:
        validate_steps(steps)
    if conditions is not None:
        validate_conditions(conditions)
    ver_num = (
        session.scalar(
            select(func.max(IntelligentWorkflowVersion.version_number)).where(
                IntelligentWorkflowVersion.workflow_id == wf.id
            )
        )
        or 0
    ) + 1
    version = IntelligentWorkflowVersion(
        organisation_id=ctx.organisation_id,
        workflow_id=wf.id,
        version_number=ver_num,
        steps_json=steps if steps is not None else _latest_steps(session, wf),
        triggers_json=triggers if triggers is not None else _latest_triggers(session, wf),
        conditions_json=conditions if conditions is not None else _latest_conditions(session, wf),
        editor_user_id=ctx.user_id,
        change_notes=data.get("change_notes"),
    )
    session.add(version)
    session.flush()
    wf.active_version_id = version.id
    wf.status = "draft"
    _audit(session, ctx, wf.id, "workflow.draft_saved", f"Saved draft v{ver_num}")
    return version


def _latest_steps(session: Session, wf: IntelligentWorkflow) -> list:
    if wf.active_version_id:
        v = session.get(IntelligentWorkflowVersion, wf.active_version_id)
        if v:
            return v.steps_json
    return []


def _latest_triggers(session: Session, wf: IntelligentWorkflow) -> list:
    if wf.active_version_id:
        v = session.get(IntelligentWorkflowVersion, wf.active_version_id)
        if v:
            return v.triggers_json
    return []


def _latest_conditions(session: Session, wf: IntelligentWorkflow) -> dict:
    if wf.active_version_id:
        v = session.get(IntelligentWorkflowVersion, wf.active_version_id)
        if v:
            return v.conditions_json
    return {}


def publish_workflow(session: Session, ctx: OrganisationContext, workflow_id: UUID) -> IntelligentWorkflow:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_MANAGE)
    assert_addon(session, get_settings(), ctx.organisation_id)
    if not _settings(session, ctx.organisation_id).privacy_review_complete:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Privacy review required before publish")
    wf = session.get(IntelligentWorkflow, workflow_id)
    if wf is None or wf.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    version = session.get(IntelligentWorkflowVersion, wf.active_version_id) if wf.active_version_id else None
    if version is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No version to publish")
    validate_steps(version.steps_json)
    validate_conditions(version.conditions_json)
    version.published_at = _now()
    wf.status = "active"
    _audit(session, ctx, wf.id, "workflow.published", f"Published v{version.version_number}")
    session.flush()
    record_event(
        session,
        action=audit_events.ADVANCED_AUTOMATION_WORKFLOW_PUBLISHED,
        resource_type="intelligent_workflow",
        resource_id=str(wf.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Published workflow {wf.name} v{version.version_number}",
    )
    return wf


def list_workflows(session: Session, ctx: OrganisationContext, status_filter: str | None) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_READ)
    q = select(IntelligentWorkflow).where(IntelligentWorkflow.organisation_id == ctx.organisation_id)
    if status_filter:
        q = q.where(IntelligentWorkflow.status == status_filter)
    rows = session.scalars(q.order_by(IntelligentWorkflow.updated_at.desc())).all()
    return [
        {
            "id": str(r.id),
            "slug": r.slug,
            "name": r.name,
            "status": r.status,
            "template_key": r.template_key,
            "active_version_id": str(r.active_version_id) if r.active_version_id else None,
        }
        for r in rows
    ]


def run_test_execution(
    session: Session,
    ctx: OrganisationContext,
    workflow_id: UUID,
    trigger_type: str,
    payload: dict[str, Any],
) -> IntelligentWorkflowExecution:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_EXECUTE)
    assert_addon(session, get_settings(), ctx.organisation_id)
    wf = session.get(IntelligentWorkflow, workflow_id)
    if wf is None or wf.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    version = session.get(IntelligentWorkflowVersion, wf.active_version_id) if wf.active_version_id else None
    if version is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Workflow has no version")
    idem = hashlib.sha256(f"test:{workflow_id}:{trigger_type}:{_now().isoformat()}".encode()).hexdigest()[:48]
    exec_row = IntelligentWorkflowExecution(
        organisation_id=ctx.organisation_id,
        workflow_id=wf.id,
        version_id=version.id,
        trigger_type=trigger_type,
        trigger_payload=payload,
        status="running",
        idempotency_key=idem,
        started_at=_now(),
        dry_run=True,
    )
    session.add(exec_row)
    session.flush()
    steps_out: list[dict[str, Any]] = []
    for step in version.steps_json:
        if not isinstance(step, dict):
            continue
        st = step.get("type")
        record = {"step_key": step.get("key"), "type": st, "status": "simulated"}
        if st == "approval":
            appr = IntelligentWorkflowApproval(
                organisation_id=ctx.organisation_id,
                execution_id=exec_row.id,
                step_key=str(step.get("key")),
                status="pending",
                required_role=step.get("required_role"),
                deadline_at=_now() + timedelta(days=3),
            )
            session.add(appr)
            record["status"] = "approval_pending"
        if st == "notification" and not exec_row.dry_run:
            record["status"] = "skipped_dry_run"
        steps_out.append(record)
    exec_row.steps_executed_json = steps_out
    exec_row.status = "completed"
    exec_row.completed_at = _now()
    session.flush()
    return exec_row


def list_executions(session: Session, ctx: OrganisationContext, limit: int = 50) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_REPORTS)
    rows = session.scalars(
        select(IntelligentWorkflowExecution)
        .where(IntelligentWorkflowExecution.organisation_id == ctx.organisation_id)
        .order_by(IntelligentWorkflowExecution.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "workflow_id": str(r.workflow_id),
            "version_id": str(r.version_id),
            "trigger_type": r.trigger_type,
            "status": r.status,
            "dry_run": r.dry_run,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]


def list_pending_approvals(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_APPROVE)
    rows = session.scalars(
        select(IntelligentWorkflowApproval).where(
            IntelligentWorkflowApproval.organisation_id == ctx.organisation_id,
            IntelligentWorkflowApproval.status == "pending",
        )
    ).all()
    return [
        {
            "id": str(r.id),
            "execution_id": str(r.execution_id),
            "step_key": r.step_key,
            "required_role": r.required_role,
            "deadline_at": r.deadline_at.isoformat() if r.deadline_at else None,
        }
        for r in rows
    ]


def decide_approval(
    session: Session,
    ctx: OrganisationContext,
    approval_id: UUID,
    *,
    approved: bool,
    comment: str | None,
) -> IntelligentWorkflowApproval:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_APPROVE)
    row = session.get(IntelligentWorkflowApproval, approval_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Approval not found")
    if row.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Approval already decided")
    row.status = "approved" if approved else "rejected"
    row.decided_by_user_id = ctx.user_id
    row.decided_at = _now()
    row.decision_comment = comment
    session.flush()
    record_event(
        session,
        action=audit_events.ADVANCED_AUTOMATION_APPROVAL_DECIDED,
        resource_type="intelligent_workflow_approval",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Workflow approval {row.status}",
    )
    return row


def ai_suggest(session: Session, ctx: OrganisationContext, prompt: str) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_AI)
    row = assert_addon(session, get_settings(), ctx.organisation_id)
    result = suggest_workflow(
        organisation_id=str(ctx.organisation_id),
        prompt=prompt,
        enabled=row.ai_assistant_enabled,
    )
    record_event(
        session,
        action=audit_events.ADVANCED_AUTOMATION_AI_SUGGEST,
        resource_type="advanced_automation",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="AI workflow suggestion requested",
    )
    return {**result, "notice": AI_NOTICE, "requires_human_publish": True}


def seed_notification_templates(session: Session, org_id: UUID) -> None:
    if session.scalar(
        select(func.count()).select_from(IntelligentWorkflowNotificationTemplate).where(
            IntelligentWorkflowNotificationTemplate.organisation_id == org_id
        )
    ):
        return
    for channel, title, body in (
        ("in_app", "Workflow update", "A workflow step completed for {{workflow_name}}."),
        ("email", "HMore workflow notification", "Hello, your organisation workflow {{workflow_name}} requires attention."),
    ):
        session.add(
            IntelligentWorkflowNotificationTemplate(
                organisation_id=org_id,
                template_slug="default",
                channel=channel,
                title_template=title,
                body_template=body,
            )
        )
    session.flush()


def schedule_workflow(
    session: Session,
    ctx: OrganisationContext,
    workflow_id: UUID,
    spec: dict[str, Any],
    timezone_name: str,
) -> IntelligentWorkflowScheduledTask:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_MANAGE)
    wf = session.get(IntelligentWorkflow, workflow_id)
    if wf is None or wf.organisation_id != ctx.organisation_id or wf.status != "active":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Active workflow required")
    row = IntelligentWorkflowScheduledTask(
        organisation_id=ctx.organisation_id,
        workflow_id=wf.id,
        timezone=timezone_name[:64],
        schedule_spec=spec,
        next_run_at=_now() + timedelta(hours=int(spec.get("delay_hours", 24))),
        status="active",
    )
    session.add(row)
    session.flush()
    return row
