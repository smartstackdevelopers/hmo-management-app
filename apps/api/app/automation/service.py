"""CRUD and dashboard for automation rules."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.automation import access
from app.automation.constants import (
    ACTION_TYPES,
    CATEGORIES,
    FORBIDDEN_ACTION_KEYS,
    FREQUENCIES,
    TRIGGER_CONDITIONS,
)
from app.db.models.automation import (
    AutomationComplianceIssue,
    AutomationEscalation,
    AutomationRule,
    AutomationRuleRun,
)
from app.db.models.scheduling import ReminderRecord
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def next_run_after(frequency: str, from_dt: datetime | None = None) -> datetime | None:
    base = from_dt or _now()
    if frequency == "manual":
        return None
    if frequency == "hourly":
        return base + timedelta(hours=1)
    if frequency == "daily":
        return base + timedelta(days=1)
    if frequency == "weekly":
        return base + timedelta(days=7)
    return base + timedelta(days=1)


def _validate_rule_payload(
    *,
    category: str,
    trigger_condition: str,
    action_type: str,
    frequency: str,
    action_config: dict[str, Any],
) -> None:
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    if trigger_condition not in TRIGGER_CONDITIONS:
        raise HTTPException(status_code=400, detail="Invalid trigger_condition")
    if action_type not in ACTION_TYPES:
        raise HTTPException(status_code=400, detail="Invalid action_type")
    if frequency not in FREQUENCIES:
        raise HTTPException(status_code=400, detail="Invalid frequency")
    forbidden = FORBIDDEN_ACTION_KEYS.intersection(set(action_config.keys()) | {action_config.get("forbidden_action")})
    if forbidden:
        raise HTTPException(
            status_code=400,
            detail=f"Forbidden automation actions: {sorted(forbidden)}",
        )
    # Category/action consistency
    if category == "reminder" and action_type not in {"create_reminder", "create_approval_request"}:
        raise HTTPException(status_code=400, detail="Reminder rules must use reminder/approval actions")
    if category == "escalation" and action_type not in {"escalate_record", "create_approval_request"}:
        raise HTTPException(status_code=400, detail="Escalation rules must escalate or request approval")
    if category == "compliance_sweep" and action_type != "run_compliance_sweep":
        raise HTTPException(status_code=400, detail="Compliance rules must run compliance sweeps")


def rule_to_dict(row: AutomationRule) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "description": row.description,
        "organisation_id": str(row.organisation_id),
        "category": row.category,
        "trigger_condition": row.trigger_condition,
        "trigger_config": row.trigger_config or {},
        "action_type": row.action_type,
        "action_config": row.action_config or {},
        "frequency": row.frequency,
        "is_enabled": row.is_enabled,
        "created_by_user_id": str(row.created_by_user_id) if row.created_by_user_id else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
    }


def run_to_dict(row: AutomationRuleRun) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "rule_id": str(row.rule_id),
        "status": row.status,
        "idempotency_key": row.idempotency_key,
        "attempt_count": row.attempt_count,
        "error_message": row.error_message,
        "result_summary": row.result_summary or {},
        "requires_human_approval": row.requires_human_approval,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def escalation_to_dict(row: AutomationEscalation) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "rule_id": str(row.rule_id) if row.rule_id else None,
        "run_id": str(row.run_id) if row.run_id else None,
        "resource_type": row.resource_type,
        "resource_id": str(row.resource_id),
        "escalation_level": row.escalation_level,
        "severity": row.severity,
        "reason": row.reason,
        "status": row.status,
        "recipient_role": row.recipient_role,
        "recipient_user_id": str(row.recipient_user_id) if row.recipient_user_id else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "resolution_note": row.resolution_note,
    }


def issue_to_dict(row: AutomationComplianceIssue) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "rule_id": str(row.rule_id) if row.rule_id else None,
        "run_id": str(row.run_id) if row.run_id else None,
        "compliance_sweep_id": str(row.compliance_sweep_id) if row.compliance_sweep_id else None,
        "issue_type": row.issue_type,
        "title": row.title,
        "severity": row.severity,
        "status": row.status,
        "related_refs": row.related_refs or {},
        "assigned_user_id": str(row.assigned_user_id) if row.assigned_user_id else None,
        "detected_at": row.detected_at.isoformat() if row.detected_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }


def create_rule(
    session: Session,
    ctx: OrganisationContext,
    *,
    name: str,
    description: str | None,
    category: str,
    trigger_condition: str,
    trigger_config: dict[str, Any] | None,
    action_type: str,
    action_config: dict[str, Any] | None,
    frequency: str,
    is_enabled: bool = True,
) -> dict[str, Any]:
    access.require_rules_manage(ctx)
    action_config = action_config or {}
    _validate_rule_payload(
        category=category,
        trigger_condition=trigger_condition,
        action_type=action_type,
        frequency=frequency,
        action_config=action_config,
    )
    row = AutomationRule(
        organisation_id=ctx.organisation_id,
        name=name.strip()[:200],
        description=description,
        category=category,
        trigger_condition=trigger_condition,
        trigger_config=trigger_config or {},
        action_type=action_type,
        action_config=action_config,
        frequency=frequency,
        is_enabled=is_enabled,
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
        next_run_at=_now() if is_enabled and frequency != "manual" else None,
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.AUTOMATION_RULE_CREATE,
        resource_type="automation_rule",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Created automation rule {row.name}",
        raise_on_error=False,
    )
    return rule_to_dict(row)


def update_rule(
    session: Session,
    ctx: OrganisationContext,
    rule_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    trigger_config: dict[str, Any] | None = None,
    action_config: dict[str, Any] | None = None,
    frequency: str | None = None,
    is_enabled: bool | None = None,
) -> dict[str, Any]:
    access.require_rules_manage(ctx)
    row = session.get(AutomationRule, rule_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Rule not found")
    if name is not None:
        row.name = name.strip()[:200]
    if description is not None:
        row.description = description
    if trigger_config is not None:
        row.trigger_config = trigger_config
    if action_config is not None:
        forbidden = FORBIDDEN_ACTION_KEYS.intersection(set(action_config.keys()))
        if forbidden:
            raise HTTPException(status_code=400, detail=f"Forbidden automation actions: {sorted(forbidden)}")
        row.action_config = action_config
    if frequency is not None:
        if frequency not in FREQUENCIES:
            raise HTTPException(status_code=400, detail="Invalid frequency")
        row.frequency = frequency
    if is_enabled is not None:
        row.is_enabled = is_enabled
        if is_enabled and row.frequency != "manual" and row.next_run_at is None:
            row.next_run_at = _now()
        if not is_enabled:
            row.next_run_at = None
    row.updated_by_user_id = ctx.user_id
    session.flush()
    record_event(
        session,
        action=audit_events.AUTOMATION_RULE_UPDATE,
        resource_type="automation_rule",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Updated automation rule {row.name}",
        raise_on_error=False,
    )
    return rule_to_dict(row)


def delete_rule(session: Session, ctx: OrganisationContext, rule_id: uuid.UUID) -> dict[str, Any]:
    access.require_rules_manage(ctx)
    row = session.get(AutomationRule, rule_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Rule not found")
    rid = row.id
    name = row.name
    session.delete(row)
    session.flush()
    record_event(
        session,
        action=audit_events.AUTOMATION_RULE_DELETE,
        resource_type="automation_rule",
        resource_id=rid,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Deleted automation rule {name}",
        raise_on_error=False,
    )
    return {"deleted": True, "id": str(rid)}


def list_rules(
    session: Session,
    ctx: OrganisationContext,
    *,
    category: str | None = None,
    is_enabled: bool | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    access.require_rules_read(ctx)
    stmt = select(AutomationRule).where(AutomationRule.organisation_id == ctx.organisation_id)
    if category:
        stmt = stmt.where(AutomationRule.category == category)
    if is_enabled is not None:
        stmt = stmt.where(AutomationRule.is_enabled.is_(is_enabled))
    if search:
        needle = f"%{search.strip()}%"
        stmt = stmt.where(AutomationRule.name.ilike(needle))
    rows = session.scalars(stmt.order_by(AutomationRule.created_at.desc())).all()
    return [rule_to_dict(r) for r in rows]


def get_rule(session: Session, ctx: OrganisationContext, rule_id: uuid.UUID) -> dict[str, Any]:
    access.require_rules_read(ctx)
    row = session.get(AutomationRule, rule_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule_to_dict(row)


def list_runs(
    session: Session,
    ctx: OrganisationContext,
    *,
    rule_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    access.require_runs_read(ctx)
    stmt = select(AutomationRuleRun).where(AutomationRuleRun.organisation_id == ctx.organisation_id)
    if rule_id:
        stmt = stmt.where(AutomationRuleRun.rule_id == rule_id)
    if status_filter:
        stmt = stmt.where(AutomationRuleRun.status == status_filter)
    rows = session.scalars(stmt.order_by(AutomationRuleRun.created_at.desc()).limit(limit)).all()
    return [run_to_dict(r) for r in rows]


def list_escalations(
    session: Session,
    ctx: OrganisationContext,
    *,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    access.require_runs_read(ctx)
    stmt = select(AutomationEscalation).where(AutomationEscalation.organisation_id == ctx.organisation_id)
    if status_filter:
        stmt = stmt.where(AutomationEscalation.status == status_filter)
    rows = session.scalars(stmt.order_by(AutomationEscalation.created_at.desc()).limit(limit)).all()
    return [escalation_to_dict(r) for r in rows]


def update_escalation_status(
    session: Session,
    ctx: OrganisationContext,
    escalation_id: uuid.UUID,
    *,
    new_status: str,
    resolution_note: str | None = None,
) -> dict[str, Any]:
    access.require_escalations_manage(ctx)
    if new_status not in {"acknowledged", "resolved", "dismissed", "open"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    row = session.get(AutomationEscalation, escalation_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Escalation not found")
    previous = row.status
    row.status = new_status
    if new_status == "acknowledged":
        row.acknowledged_at = _now()
        row.acknowledged_by_user_id = ctx.user_id
    if new_status in {"resolved", "dismissed"}:
        row.resolved_at = _now()
        row.resolution_note = resolution_note
    session.flush()
    record_event(
        session,
        action=audit_events.AUTOMATION_ESCALATION_STATUS,
        resource_type="automation_escalation",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Escalation status {previous} → {new_status}",
        metadata={"from": previous, "to": new_status},
        raise_on_error=False,
    )
    return escalation_to_dict(row)


def list_compliance_issues(
    session: Session,
    ctx: OrganisationContext,
    *,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    access.require_runs_read(ctx)
    stmt = select(AutomationComplianceIssue).where(
        AutomationComplianceIssue.organisation_id == ctx.organisation_id
    )
    if status_filter:
        stmt = stmt.where(AutomationComplianceIssue.status == status_filter)
    rows = session.scalars(stmt.order_by(AutomationComplianceIssue.detected_at.desc()).limit(limit)).all()
    return [issue_to_dict(r) for r in rows]


def dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    access.require_rules_read(ctx)
    org = ctx.organisation_id
    total_rules = int(
        session.scalar(select(func.count()).select_from(AutomationRule).where(AutomationRule.organisation_id == org))
        or 0
    )
    active_rules = int(
        session.scalar(
            select(func.count())
            .select_from(AutomationRule)
            .where(AutomationRule.organisation_id == org, AutomationRule.is_enabled.is_(True))
        )
        or 0
    )
    succeeded = int(
        session.scalar(
            select(func.count())
            .select_from(AutomationRuleRun)
            .where(AutomationRuleRun.organisation_id == org, AutomationRuleRun.status == "succeeded")
        )
        or 0
    )
    failed = int(
        session.scalar(
            select(func.count())
            .select_from(AutomationRuleRun)
            .where(AutomationRuleRun.organisation_id == org, AutomationRuleRun.status == "failed")
        )
        or 0
    )
    pending_reminders = int(
        session.scalar(
            select(func.count())
            .select_from(ReminderRecord)
            .where(ReminderRecord.organisation_id == org, ReminderRecord.status == "pending")
        )
        or 0
    )
    sent_reminders = int(
        session.scalar(
            select(func.count())
            .select_from(ReminderRecord)
            .where(ReminderRecord.organisation_id == org, ReminderRecord.status == "sent")
        )
        or 0
    )
    active_escalations = int(
        session.scalar(
            select(func.count())
            .select_from(AutomationEscalation)
            .where(
                AutomationEscalation.organisation_id == org,
                AutomationEscalation.status.in_(("open", "acknowledged")),
            )
        )
        or 0
    )
    open_issues = int(
        session.scalar(
            select(func.count())
            .select_from(AutomationComplianceIssue)
            .where(
                AutomationComplianceIssue.organisation_id == org,
                AutomationComplianceIssue.status.in_(("open", "assigned")),
            )
        )
        or 0
    )
    recent = list_runs(session, ctx, limit=10)
    return {
        "generated_at": _now().isoformat(),
        "total_rules": total_rules,
        "active_rules": active_rules,
        "disabled_rules": max(0, total_rules - active_rules),
        "successful_executions": succeeded,
        "failed_executions": failed,
        "pending_reminders": pending_reminders,
        "sent_reminders": sent_reminders,
        "active_escalations": active_escalations,
        "open_compliance_issues": open_issues,
        "recent_runs": recent,
    }
