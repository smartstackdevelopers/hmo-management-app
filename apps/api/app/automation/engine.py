"""Execute automation rules against live operational records (F6.3)."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.automation.constants import DEFAULT_LEAD_DAYS, FORBIDDEN_ACTION_KEYS
from app.automation.service import next_run_after
from app.compliance_agent import service as compliance_service
from app.core.config import get_settings
from app.db.models.automation import (
    AutomationComplianceIssue,
    AutomationEscalation,
    AutomationRule,
    AutomationRuleRun,
)
from app.db.models.complaints import Complaint
from app.db.models.compliance import SafeguardingReminder
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.db.models.landlord_enterprise import PropertyInspection
from app.db.models.maintenance import MaintenanceRequest
from app.db.models.managed_documents import ManagedDocument
from app.db.models.membership import OrganisationMembership
from app.db.models.scheduling import OperationalTask, ReminderRecord, TenantVisit
from app.db.models.support_plans import TenantSupportPlan
from app.db.models.tenant_timeline import TenantFollowUp
from app.db.models.user import User
from app.ops.notifications import CommunicationNotificationProvider, ReminderMessage
from app.rbac.context import AuthorizationContext, MembershipView
from app.reporting.complaints_reports import OPEN_STATUSES
from app.tenancy.context import OrganisationContext

logger = logging.getLogger("hmore.automation.engine")

OPEN_FOLLOWUP = ("open", "in_progress", "awaiting_information")
OPEN_TASK = ("open", "in_progress", "blocked", "pending")
HIGH_MAINT = ("urgent", "high", "emergency")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return date.today()


def _system_ctx(session: Session, organisation_id: uuid.UUID, actor_user_id: uuid.UUID | None) -> OrganisationContext:
    membership = None
    user = session.get(User, actor_user_id) if actor_user_id else None
    if user is not None:
        membership = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == organisation_id,
                OrganisationMembership.user_id == user.id,
                OrganisationMembership.status == MembershipStatus.ACTIVE,
            )
        )
    if membership is None:
        membership = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == organisation_id,
                OrganisationMembership.role == HMoreRole.ORGANISATION_ADMIN,
                OrganisationMembership.status == MembershipStatus.ACTIVE,
            )
        )
        if membership is None:
            raise RuntimeError(f"No organisation admin for automation in {organisation_id}")
        user = session.get(User, membership.user_id)
    assert user is not None and membership is not None
    return OrganisationContext(
        user=user,
        organisation_id=organisation_id,
        role=membership.role,
        authorization=AuthorizationContext(
            user=user,
            memberships=[
                MembershipView(
                    membership_id=membership.id,
                    role=membership.role,
                    organisation_id=organisation_id,
                    status=MembershipStatus.ACTIVE,
                )
            ],
            active_organisation_id=organisation_id,
            active_role=membership.role,
        ),
    )


def _recipient_user_ids(
    session: Session,
    organisation_id: uuid.UUID,
    action_config: dict[str, Any],
    fallback: uuid.UUID | None,
) -> list[uuid.UUID]:
    explicit = action_config.get("recipient_user_ids") or []
    out: list[uuid.UUID] = []
    for raw in explicit:
        try:
            uid = uuid.UUID(str(raw))
        except ValueError:
            continue
        membership = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == organisation_id,
                OrganisationMembership.user_id == uid,
                OrganisationMembership.status == MembershipStatus.ACTIVE,
            )
        )
        if membership is not None:
            out.append(uid)
    if out:
        return out
    role_name = action_config.get("recipient_role") or "organisation_admin"
    try:
        role = HMoreRole(role_name)
    except ValueError:
        role = HMoreRole.ORGANISATION_ADMIN
    members = session.scalars(
        select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.role == role,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    ids = [m.user_id for m in members]
    if ids:
        return ids
    return [fallback] if fallback else []


def _upsert_reminder(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    reminder_kind: str,
    recipient_user_id: uuid.UUID,
    scheduled_for: datetime,
    channel: str,
    summary: str,
) -> bool:
    """Insert ReminderRecord; return False if duplicate (idempotent)."""
    existing = session.scalar(
        select(ReminderRecord).where(
            ReminderRecord.organisation_id == organisation_id,
            ReminderRecord.resource_type == resource_type,
            ReminderRecord.resource_id == resource_id,
            ReminderRecord.reminder_kind == reminder_kind,
            ReminderRecord.scheduled_for == scheduled_for,
        )
    )
    if existing is not None:
        return False
    try:
        with session.begin_nested():
            session.add(
                ReminderRecord(
                    organisation_id=organisation_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    reminder_kind=reminder_kind,
                    recipient_user_id=recipient_user_id,
                    scheduled_for=scheduled_for,
                    status="pending",
                    channel=channel,
                    payload_summary=summary[:255],
                )
            )
            session.flush()
        return True
    except IntegrityError:
        return False


def _create_escalation(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    rule: AutomationRule,
    run: AutomationRuleRun,
    resource_type: str,
    resource_id: uuid.UUID,
    reason: str,
    level: int,
    severity: str,
    recipient_role: str | None,
    recipient_user_id: uuid.UUID | None,
    day_key: str,
) -> bool:
    key = f"{rule.id}:{resource_type}:{resource_id}:{level}:{day_key}"
    existing = session.scalar(
        select(AutomationEscalation).where(
            AutomationEscalation.organisation_id == organisation_id,
            AutomationEscalation.idempotency_key == key,
        )
    )
    if existing is not None:
        return False
    try:
        with session.begin_nested():
            session.add(
                AutomationEscalation(
                    organisation_id=organisation_id,
                    rule_id=rule.id,
                    run_id=run.id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    escalation_level=level,
                    severity=severity,
                    reason=reason,
                    status="open",
                    recipient_role=recipient_role,
                    recipient_user_id=recipient_user_id,
                    idempotency_key=key,
                )
            )
            session.flush()
        return True
    except IntegrityError:
        return False


def _collect_targets(session: Session, rule: AutomationRule) -> list[dict[str, Any]]:
    """Return candidate records for the rule trigger from live DB data."""
    org = rule.organisation_id
    cfg = rule.trigger_config or {}
    lead_days = int(cfg.get("lead_days", DEFAULT_LEAD_DAYS))
    overdue_grace_hours = int(cfg.get("overdue_grace_hours", 0))
    now = _now()
    today = _today()
    upcoming_until = today + timedelta(days=lead_days)
    cond = rule.trigger_condition
    targets: list[dict[str, Any]] = []

    if cond in {"appointment_upcoming", "appointment_overdue"}:
        visits = session.scalars(
            select(TenantVisit).where(
                TenantVisit.organisation_id == org,
                TenantVisit.status.in_(("scheduled", "confirmed")),
            )
        ).all()
        for v in visits:
            if cond == "appointment_upcoming" and today <= v.scheduled_at.date() <= upcoming_until:
                targets.append(
                    {
                        "resource_type": "tenant_visit",
                        "resource_id": v.id,
                        "kind": "appointment_upcoming",
                        "summary": f"Upcoming appointment {v.id}",
                        "assignee": v.assigned_staff_user_id,
                        "when": v.scheduled_at,
                    }
                )
            if cond == "appointment_overdue" and v.scheduled_at < now - timedelta(hours=overdue_grace_hours):
                targets.append(
                    {
                        "resource_type": "tenant_visit",
                        "resource_id": v.id,
                        "kind": "appointment_overdue",
                        "summary": f"Overdue appointment {v.id}",
                        "assignee": v.assigned_staff_user_id,
                        "when": v.scheduled_at,
                    }
                )

    if cond in {"support_plan_review_upcoming", "support_plan_review_overdue"}:
        plans = session.scalars(
            select(TenantSupportPlan).where(
                TenantSupportPlan.organisation_id == org,
                TenantSupportPlan.status.in_(("active", "under_review")),
                TenantSupportPlan.planned_review_date.is_not(None),
            )
        ).all()
        for p in plans:
            assert p.planned_review_date is not None
            if cond == "support_plan_review_upcoming" and today <= p.planned_review_date <= upcoming_until:
                targets.append(
                    {
                        "resource_type": "tenant_support_plan",
                        "resource_id": p.id,
                        "kind": "support_plan_review_upcoming",
                        "summary": f"Plan review due {p.reference_number}",
                        "assignee": p.responsible_worker_user_id,
                        "when": datetime.combine(p.planned_review_date, datetime.min.time(), tzinfo=timezone.utc),
                    }
                )
            if cond == "support_plan_review_overdue" and p.planned_review_date < today:
                targets.append(
                    {
                        "resource_type": "tenant_support_plan",
                        "resource_id": p.id,
                        "kind": "support_plan_review_overdue",
                        "summary": f"Overdue plan review {p.reference_number}",
                        "assignee": p.responsible_worker_user_id,
                        "when": datetime.combine(p.planned_review_date, datetime.min.time(), tzinfo=timezone.utc),
                    }
                )

    if cond in {"task_pending", "task_overdue", "task_overdue_escalation"}:
        tasks = session.scalars(
            select(OperationalTask).where(
                OperationalTask.organisation_id == org,
                OperationalTask.status.in_(OPEN_TASK),
            )
        ).all()
        for t in tasks:
            if cond == "task_pending" and t.due_at and today <= t.due_at.date() <= upcoming_until:
                targets.append(
                    {
                        "resource_type": "operational_task",
                        "resource_id": t.id,
                        "kind": "task_pending",
                        "summary": f"Pending task {t.id}",
                        "assignee": t.assigned_user_id,
                        "when": t.due_at,
                    }
                )
            if cond in {"task_overdue", "task_overdue_escalation"} and t.due_at and t.due_at < now:
                targets.append(
                    {
                        "resource_type": "operational_task",
                        "resource_id": t.id,
                        "kind": "task_overdue",
                        "summary": f"Overdue task {t.id}",
                        "assignee": t.assigned_user_id,
                        "when": t.due_at,
                    }
                )

    if cond in {"inspection_upcoming", "inspection_overdue", "inspection_missed"}:
        inspections = session.scalars(
            select(PropertyInspection).where(
                PropertyInspection.organisation_id == org,
                PropertyInspection.is_archived.is_(False),
            )
        ).all()
        for insp in inspections:
            if insp.status in {"completed", "cancelled"}:
                continue
            sched = insp.scheduled_date
            if cond == "inspection_upcoming" and today <= sched <= upcoming_until:
                targets.append(
                    {
                        "resource_type": "property_inspection",
                        "resource_id": insp.id,
                        "kind": "inspection_upcoming",
                        "summary": f"Upcoming inspection {insp.id}",
                        "assignee": insp.assigned_to_user_id,
                        "when": datetime.combine(sched, datetime.min.time(), tzinfo=timezone.utc),
                    }
                )
            if cond in {"inspection_overdue", "inspection_missed"} and sched < today and insp.status != "completed":
                targets.append(
                    {
                        "resource_type": "property_inspection",
                        "resource_id": insp.id,
                        "kind": "inspection_overdue",
                        "summary": f"Overdue inspection {insp.id}",
                        "assignee": insp.assigned_to_user_id,
                        "when": datetime.combine(sched, datetime.min.time(), tzinfo=timezone.utc),
                    }
                )

    if cond == "document_expiry":
        docs = session.scalars(
            select(ManagedDocument).where(
                ManagedDocument.organisation_id == org,
                ManagedDocument.expiry_date.is_not(None),
            )
        ).all()
        for d in docs:
            assert d.expiry_date is not None
            if d.expiry_date <= upcoming_until:
                targets.append(
                    {
                        "resource_type": "managed_document",
                        "resource_id": d.id,
                        "kind": "document_expiry",
                        "summary": f"Document expiry {d.id}",
                        "assignee": d.uploaded_by_user_id,
                        "when": datetime.combine(d.expiry_date, datetime.min.time(), tzinfo=timezone.utc),
                    }
                )

    if cond in {"complaint_action_required", "complaint_overdue"}:
        complaints = session.scalars(
            select(Complaint).where(
                Complaint.organisation_id == org,
                Complaint.status.in_(tuple(OPEN_STATUSES)),
            )
        ).all()
        for c in complaints:
            due = c.response_due_at
            if cond == "complaint_action_required":
                targets.append(
                    {
                        "resource_type": "complaint",
                        "resource_id": c.id,
                        "kind": "complaint_action_required",
                        "summary": f"Complaint needs action {c.reference_number}",
                        "assignee": c.assigned_user_id,
                        "when": due or now,
                    }
                )
            if cond == "complaint_overdue" and due is not None and due < now:
                targets.append(
                    {
                        "resource_type": "complaint",
                        "resource_id": c.id,
                        "kind": "complaint_overdue",
                        "summary": f"Overdue complaint {c.reference_number}",
                        "assignee": c.assigned_user_id,
                        "when": due,
                    }
                )

    if cond in {"maintenance_scheduled", "maintenance_high_priority"}:
        reqs = session.scalars(
            select(MaintenanceRequest).where(MaintenanceRequest.organisation_id == org)
        ).all()
        for m in reqs:
            if m.status in {"completed", "cancelled", "closed"}:
                continue
            if cond == "maintenance_scheduled":
                targets.append(
                    {
                        "resource_type": "maintenance_request",
                        "resource_id": m.id,
                        "kind": "maintenance_scheduled",
                        "summary": f"Maintenance {m.reference_number}",
                        "assignee": m.assigned_user_id,
                        "when": m.reported_at or now,
                    }
                )
            if cond == "maintenance_high_priority" and (m.priority or "").lower() in HIGH_MAINT:
                targets.append(
                    {
                        "resource_type": "maintenance_request",
                        "resource_id": m.id,
                        "kind": "maintenance_high_priority",
                        "summary": f"High-priority maintenance {m.reference_number}",
                        "assignee": m.assigned_user_id,
                        "when": m.reported_at or now,
                    }
                )

    if cond == "followup_missed":
        fus = session.scalars(
            select(TenantFollowUp).where(
                TenantFollowUp.organisation_id == org,
                TenantFollowUp.status.in_(OPEN_FOLLOWUP),
                TenantFollowUp.due_at.is_not(None),
                TenantFollowUp.due_at < now,
            )
        ).all()
        for f in fus:
            targets.append(
                {
                    "resource_type": "tenant_follow_up",
                    "resource_id": f.id,
                    "kind": "followup_missed",
                    "summary": f"Missed follow-up {f.id}",
                    "assignee": f.assigned_user_id,
                    "when": f.due_at,
                }
            )

    if cond == "safeguarding_followup_overdue":
        rows = session.scalars(
            select(SafeguardingReminder).where(
                SafeguardingReminder.organisation_id == org,
                SafeguardingReminder.status.in_(("open", "pending", "overdue")),
            )
        ).all()
        for s in rows:
            due = getattr(s, "due_at", None) or getattr(s, "due_date", None)
            overdue = False
            if isinstance(due, datetime) and due < now:
                overdue = True
            if isinstance(due, date) and not isinstance(due, datetime) and due < today:
                overdue = True
            if overdue or getattr(s, "status", "") == "overdue":
                targets.append(
                    {
                        "resource_type": "safeguarding_reminder",
                        "resource_id": s.id,
                        "kind": "safeguarding_followup_overdue",
                        "summary": f"Overdue safeguarding follow-up {s.id}",
                        "assignee": getattr(s, "assigned_user_id", None),
                        "when": due if isinstance(due, datetime) else now,
                    }
                )

    if cond == "compliance_scheduled_sweep":
        targets.append(
            {
                "resource_type": "organisation",
                "resource_id": org,
                "kind": "compliance_scheduled_sweep",
                "summary": "Scheduled compliance sweep",
                "assignee": None,
                "when": now,
            }
        )

    return targets


def _notify(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
    subject: str,
    body: str,
    target_type: str,
    target_id: str,
    channel: str = "in_app",
) -> None:
    provider = CommunicationNotificationProvider()
    provider.send(
        session,
        ReminderMessage(
            organisation_id=str(organisation_id),
            recipient_user_id=str(recipient_user_id),
            subject=subject,
            body=body,
            channel=channel if channel in {"in_app", "email", "sms", "push"} else "in_app",
            target_type=target_type,
            target_id=target_id,
            idempotency_key=f"automation:{target_type}:{target_id}:{recipient_user_id}:{channel}",
            essential_operational=True,
        ),
    )


def execute_rule(
    session: Session,
    rule_id: uuid.UUID,
    *,
    force: bool = False,
    retry_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    rule = session.get(AutomationRule, rule_id)
    if rule is None:
        return {"ok": False, "error": "rule_not_found"}
    if not rule.is_enabled and not force and retry_run_id is None:
        return {"ok": False, "error": "rule_disabled"}

    # Block forbidden action keys in stored config
    action_cfg = dict(rule.action_config or {})
    if FORBIDDEN_ACTION_KEYS.intersection(action_cfg.keys()):
        return {"ok": False, "error": "forbidden_action_config"}

    day_key = _today().isoformat()
    hour_key = _now().strftime("%Y%m%d%H")
    idem = f"rule:{rule.id}:{day_key if rule.frequency != 'hourly' else hour_key}"
    if retry_run_id:
        run = session.get(AutomationRuleRun, retry_run_id)
        if run is None or run.rule_id != rule.id:
            return {"ok": False, "error": "run_not_found"}
        if run.attempt_count >= 5:
            return {"ok": False, "error": "max_retries"}
        run.status = "running"
        run.attempt_count = int(run.attempt_count or 0) + 1
        run.started_at = _now()
        run.error_message = None
        idem = run.idempotency_key
    else:
        existing = session.scalar(
            select(AutomationRuleRun).where(
                AutomationRuleRun.organisation_id == rule.organisation_id,
                AutomationRuleRun.idempotency_key == idem,
            )
        )
        if existing is not None and existing.status in {"succeeded", "running", "pending"}:
            return {"ok": True, "skipped": True, "run_id": str(existing.id), "reason": "duplicate_prevented"}
        run = AutomationRuleRun(
            organisation_id=rule.organisation_id,
            rule_id=rule.id,
            status="running",
            idempotency_key=idem,
            started_at=_now(),
            attempt_count=1,
            requires_human_approval=bool(action_cfg.get("require_human_approval"))
            or rule.action_type == "create_approval_request",
        )
        try:
            with session.begin_nested():
                session.add(run)
                session.flush()
        except IntegrityError:
            existing = session.scalar(
                select(AutomationRuleRun).where(
                    AutomationRuleRun.organisation_id == rule.organisation_id,
                    AutomationRuleRun.idempotency_key == idem,
                )
            )
            return {
                "ok": True,
                "skipped": True,
                "run_id": str(existing.id) if existing else None,
                "reason": "duplicate_prevented",
            }

    try:
        ctx = _system_ctx(session, rule.organisation_id, rule.created_by_user_id)
        channels = action_cfg.get("channels") or ["in_app"]
        if isinstance(channels, str):
            channels = [channels]
        level = int(action_cfg.get("escalation_level", 1))
        severity = action_cfg.get("severity", "warning")
        created_reminders = 0
        created_escalations = 0
        created_issues = 0
        notified = 0
        approval_flagged = 0

        if rule.action_type == "run_compliance_sweep" or rule.trigger_condition == "compliance_scheduled_sweep":
            # Call service directly (avoid compliance job's session.commit inside our unit of work)
            sweep_result = compliance_service.run_sweep(
                session,
                ctx,
                trigger=f"automation_rule:{rule.id}",
                settings=get_settings(),
            )
            findings = int(sweep_result.get("findings_created") or 0)
            issue_key = f"sweep:{rule.id}:{day_key}"
            existing_issue = session.scalar(
                select(AutomationComplianceIssue).where(
                    AutomationComplianceIssue.organisation_id == rule.organisation_id,
                    AutomationComplianceIssue.idempotency_key == issue_key,
                )
            )
            if existing_issue is None:
                try:
                    with session.begin_nested():
                        session.add(
                            AutomationComplianceIssue(
                                organisation_id=rule.organisation_id,
                                rule_id=rule.id,
                                run_id=run.id,
                                compliance_sweep_id=uuid.UUID(str(sweep_result["id"]))
                                if sweep_result.get("id")
                                else None,
                                issue_type="compliance_sweep_completed",
                                title=f"Compliance sweep completed ({findings} findings)",
                                severity="warning" if findings else "info",
                                status="open" if findings else "resolved",
                                related_refs={
                                    "sweep_id": sweep_result.get("id"),
                                    "findings_created": findings,
                                    "status": sweep_result.get("status"),
                                },
                                assigned_user_id=rule.created_by_user_id,
                                detected_at=_now(),
                                resolved_at=None if findings else _now(),
                                idempotency_key=issue_key,
                            )
                        )
                        session.flush()
                    created_issues = 1
                except IntegrityError:
                    pass
            run.status = "succeeded"
            run.finished_at = _now()
            run.result_summary = {
                "sweep_id": sweep_result.get("id"),
                "findings_created": findings,
                "issues_recorded": created_issues,
                "requires_human_approval": run.requires_human_approval,
            }
            rule.last_run_at = _now()
            rule.next_run_at = next_run_after(rule.frequency, _now())
            session.flush()
            return {"ok": True, "run_id": str(run.id), "result": run.result_summary}

        targets = _collect_targets(session, rule)
        for target in targets:
            recipients = _recipient_user_ids(
                session,
                rule.organisation_id,
                action_cfg,
                target.get("assignee") or rule.created_by_user_id,
            )
            if not recipients:
                continue

            if rule.action_type == "create_approval_request" or action_cfg.get("require_human_approval"):
                # Safety: do not auto-decide; flag for human review via notification
                approval_flagged += 1
                for uid in recipients:
                    _notify(
                        session,
                        organisation_id=rule.organisation_id,
                        recipient_user_id=uid,
                        subject=f"Human approval required: {rule.name}",
                        body=(
                            f"Automation rule '{rule.name}' detected {target['kind']} "
                            f"on {target['resource_type']} {target['resource_id']}. "
                            f"No sensitive decision was applied. Please review."
                        ),
                        target_type="automation_approval",
                        target_id=f"{run.id}:{target['resource_id']}",
                        channel=channels[0],
                    )
                    notified += 1
                continue

            if rule.action_type == "create_reminder":
                scheduled_for = target.get("when") or _now()
                if isinstance(scheduled_for, date) and not isinstance(scheduled_for, datetime):
                    scheduled_for = datetime.combine(scheduled_for, datetime.min.time(), tzinfo=timezone.utc)
                # Normalize to minute for idempotency uniqueness
                scheduled_for = scheduled_for.replace(second=0, microsecond=0)
                for uid in recipients:
                    for channel in channels:
                        if _upsert_reminder(
                            session,
                            organisation_id=rule.organisation_id,
                            resource_type=target["resource_type"],
                            resource_id=target["resource_id"],
                            reminder_kind=f"automation:{target['kind']}",
                            recipient_user_id=uid,
                            scheduled_for=scheduled_for,
                            channel=channel,
                            summary=str(target["summary"]),
                        ):
                            created_reminders += 1
                            _notify(
                                session,
                                organisation_id=rule.organisation_id,
                                recipient_user_id=uid,
                                subject=f"Reminder: {rule.name}",
                                body=str(target["summary"]),
                                target_type="automation_reminder",
                                target_id=f"{run.id}:{target['resource_id']}:{channel}",
                                channel=channel,
                            )
                            notified += 1

            elif rule.action_type == "escalate_record":
                primary = recipients[0]
                if _create_escalation(
                    session,
                    organisation_id=rule.organisation_id,
                    rule=rule,
                    run=run,
                    resource_type=target["resource_type"],
                    resource_id=target["resource_id"],
                    reason=str(target["summary"]),
                    level=level,
                    severity=severity if severity in {"info", "warning", "high", "critical"} else "warning",
                    recipient_role=action_cfg.get("recipient_role"),
                    recipient_user_id=primary,
                    day_key=day_key,
                ):
                    created_escalations += 1
                    for uid in recipients:
                        _notify(
                            session,
                            organisation_id=rule.organisation_id,
                            recipient_user_id=uid,
                            subject=f"Escalation: {rule.name}",
                            body=f"{target['summary']} (level {level}). Human review required.",
                            target_type="automation_escalation",
                            target_id=f"{run.id}:{target['resource_id']}",
                            channel=channels[0],
                        )
                        notified += 1

        run.status = "succeeded"
        run.finished_at = _now()
        run.result_summary = {
            "targets": len(targets),
            "reminders_created": created_reminders,
            "escalations_created": created_escalations,
            "notifications": notified,
            "approval_requests_flagged": approval_flagged,
        }
        rule.last_run_at = _now()
        rule.next_run_at = next_run_after(rule.frequency, _now())
        session.flush()
        return {"ok": True, "run_id": str(run.id), "result": run.result_summary}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Automation rule failed rule_id=%s", rule_id)
        run.status = "failed"
        run.finished_at = _now()
        run.error_message = str(exc)[:2000]
        rule.next_run_at = _now() + timedelta(minutes=15)
        session.flush()
        return {"ok": False, "run_id": str(run.id), "error": str(exc)[:500]}
