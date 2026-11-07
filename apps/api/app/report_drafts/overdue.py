"""Scan existing overdue sources and upsert ReminderRecord rows (idempotent)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models import Organisation
from app.db.models.compliance import SafeguardingReminder
from app.db.models.enums import RecordStatus
from app.db.models.incidents import IncidentFollowUp
from app.db.models.scheduling import OperationalTask, ReminderRecord
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

logger = logging.getLogger("hmore.overdue_reminders")

OPEN_TASKS = ("open", "in_progress", "blocked")
OPEN_FOLLOW_UPS = ("open", "in_progress", "blocked")
OPEN_SAFEGUARDING = ("pending", "sent", "acknowledged", "overdue")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _floor_minute(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.replace(second=0, microsecond=0)


def _upsert_overdue(
    session: Session,
    *,
    organisation_id,
    resource_type: str,
    resource_id,
    reminder_kind: str,
    recipient_user_id,
    due_at: datetime,
    summary: str,
) -> str:
    scheduled_for = _floor_minute(due_at)
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
        record_event(
            session,
            action=audit_events.OVERDUE_REMINDER_DEDUPED,
            resource_type="reminder_record",
            resource_id=str(existing.id),
            organisation_id=organisation_id,
            actor_user_id=None,
            outcome=AuditOutcome.SUCCESS,
            summary="Duplicate overdue reminder prevented",
            metadata={"kind": reminder_kind, "resource_type": resource_type},
            raise_on_error=False,
        )
        return "deduped"
    row = ReminderRecord(
        organisation_id=organisation_id,
        resource_type=resource_type,
        resource_id=resource_id,
        reminder_kind=reminder_kind,
        recipient_user_id=recipient_user_id,
        scheduled_for=scheduled_for,
        status="pending",
        channel="in_app",
        payload_summary=summary[:255],
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.OVERDUE_REMINDER_SCHEDULED,
        resource_type="reminder_record",
        resource_id=str(row.id),
        organisation_id=organisation_id,
        actor_user_id=None,
        outcome=AuditOutcome.SUCCESS,
        summary="Overdue reminder scheduled",
        metadata={"kind": reminder_kind, "resource_type": resource_type},
        raise_on_error=False,
    )
    return "scheduled"


def scan_organisation(session: Session, organisation_id) -> dict[str, int]:
    apply_organisation_rls(session, organisation_id)
    now = _now()
    counts = {"detected": 0, "scheduled": 0, "deduped": 0}
    tasks = session.scalars(
        select(OperationalTask).where(
            OperationalTask.organisation_id == organisation_id,
            OperationalTask.status.in_(OPEN_TASKS),
            OperationalTask.due_at.is_not(None),
            OperationalTask.due_at < now,
        ).limit(500)
    )
    for task in tasks:
        counts["detected"] += 1
        result = _upsert_overdue(
            session,
            organisation_id=organisation_id,
            resource_type="operational_task",
            resource_id=task.id,
            reminder_kind="task_overdue",
            recipient_user_id=task.assigned_user_id,
            due_at=task.due_at,
            summary=f"Task overdue: {task.title}",
        )
        counts[result] += 1

    follow_ups = session.scalars(
        select(IncidentFollowUp).where(
            IncidentFollowUp.organisation_id == organisation_id,
            IncidentFollowUp.status.in_(OPEN_FOLLOW_UPS),
            IncidentFollowUp.due_at.is_not(None),
            IncidentFollowUp.due_at < now,
        ).limit(500)
    )
    for action in follow_ups:
        counts["detected"] += 1
        result = _upsert_overdue(
            session,
            organisation_id=organisation_id,
            resource_type="incident_follow_up",
            resource_id=action.id,
            reminder_kind="incident_follow_up_overdue",
            recipient_user_id=action.assigned_user_id,
            due_at=action.due_at,
            summary="Incident follow-up overdue",
        )
        counts[result] += 1

    safeguarding = session.scalars(
        select(SafeguardingReminder).where(
            SafeguardingReminder.organisation_id == organisation_id,
            SafeguardingReminder.status.in_(OPEN_SAFEGUARDING),
            SafeguardingReminder.due_at < now,
        ).limit(500)
    )
    for item in safeguarding:
        counts["detected"] += 1
        result = _upsert_overdue(
            session,
            organisation_id=organisation_id,
            resource_type="safeguarding_reminder",
            resource_id=item.id,
            reminder_kind="safeguarding_overdue",
            recipient_user_id=item.assigned_user_id,
            due_at=item.due_at,
            summary=f"Safeguarding reminder overdue: {item.title}",
        )
        counts[result] += 1
    session.flush()
    return counts


def dispatch_overdue_scans(session: Session) -> dict:
    apply_platform_rls_bypass(session)
    totals = {"organisations": 0, "detected": 0, "scheduled": 0, "deduped": 0, "failed": 0}
    for org in session.scalars(select(Organisation).where(Organisation.status == RecordStatus.ACTIVE)):
        totals["organisations"] += 1
        try:
            result = scan_organisation(session, org.id)
            session.commit()
            apply_platform_rls_bypass(session)
            totals["detected"] += result["detected"]
            totals["scheduled"] += result["scheduled"]
            totals["deduped"] += result["deduped"]
        except Exception:  # noqa: BLE001
            session.rollback()
            apply_platform_rls_bypass(session)
            totals["failed"] += 1
            logger.exception("Overdue reminder scan failed organisation_id=%s", org.id)
    return totals
