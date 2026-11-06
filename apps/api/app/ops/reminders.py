"""Reminder dispatch — rechecks live resource state before delivery (F2.2)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import get_settings
from app.db.models.compliance import SafeguardingReminder, StaffTrainingRecord
from app.db.models.scheduling import OperationalTask, ReminderRecord, StaffShift, TenantVisit
from app.ops.notifications import ReminderMessage, get_notification_provider
from app.tenancy.jobs import JobOrganisationContext, validate_job_organisation_context
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

logger = logging.getLogger("hmore.reminders")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resource_still_active(session: Session, reminder: ReminderRecord) -> tuple[bool, str]:
    if reminder.resource_type == "staff_shift":
        shift = session.get(StaffShift, reminder.resource_id)
        if shift is None or shift.organisation_id != reminder.organisation_id:
            return False, "shift_missing"
        if shift.status != "scheduled":
            return False, f"shift_{shift.status}"
        return True, "ok"
    if reminder.resource_type == "tenant_visit":
        visit = session.get(TenantVisit, reminder.resource_id)
        if visit is None or visit.organisation_id != reminder.organisation_id:
            return False, "visit_missing"
        if visit.status in {"cancelled", "completed", "missed"}:
            return False, f"visit_{visit.status}"
        return True, "ok"
    if reminder.resource_type == "operational_task":
        task = session.get(OperationalTask, reminder.resource_id)
        if task is None or task.organisation_id != reminder.organisation_id:
            return False, "task_missing"
        if task.status in {"completed", "cancelled"}:
            return False, f"task_{task.status}"
        if reminder.reminder_kind == "task_overdue":
            if task.due_at is None or task.due_at > _now():
                return False, "task_not_overdue"
        return True, "ok"
    if reminder.resource_type == "staff_training":
        training = session.get(StaffTrainingRecord, reminder.resource_id)
        if training is None or training.organisation_id != reminder.organisation_id:
            return False, "training_missing"
        if training.status == "exempt":
            return False, "training_exempt"
        if reminder.reminder_kind == "training_incomplete_due":
            if training.status not in {"not_started", "in_progress"}:
                return False, f"training_{training.status}"
            return True, "ok"
        if reminder.reminder_kind in {"training_expiring_soon", "training_expired"}:
            if training.status != "completed" or training.expiry_date is None:
                return False, "training_not_expiring"
            return True, "ok"
        return True, "ok"
    if reminder.resource_type == "safeguarding_reminder":
        sg = session.get(SafeguardingReminder, reminder.resource_id)
        if sg is None or sg.organisation_id != reminder.organisation_id:
            return False, "safeguarding_missing"
        if sg.status in {"completed", "cancelled"}:
            return False, f"safeguarding_{sg.status}"
        if reminder.reminder_kind == "safeguarding_overdue":
            if sg.due_at > _now():
                return False, "safeguarding_not_overdue"
            if sg.status in {"pending", "sent", "acknowledged"}:
                sg.status = "overdue"
        elif reminder.reminder_kind == "safeguarding_upcoming":
            if sg.status == "pending":
                # Mark as sent after successful delivery (caller updates ReminderRecord).
                pass
        return True, "ok"
    return False, "unknown_resource"


def dispatch_due_reminders(session: Session, *, limit: int | None = None) -> dict[str, int]:
    """Process pending reminders that are due. Idempotent per reminder row."""
    settings = get_settings()
    batch = limit or settings.reminder_dispatch_batch_size
    apply_platform_rls_bypass(session)
    due = list(
        session.scalars(
            select(ReminderRecord)
            .where(
                ReminderRecord.status == "pending",
                ReminderRecord.scheduled_for <= _now(),
            )
            .order_by(ReminderRecord.scheduled_for.asc())
            .limit(batch)
        ).all()
    )
    counts = {"sent": 0, "failed": 0, "skipped": 0, "processed": 0}
    provider = get_notification_provider()
    for reminder in due:
        counts["processed"] += 1
        apply_organisation_rls(session, reminder.organisation_id)
        active, reason = _resource_still_active(session, reminder)
        reminder.attempt_count += 1
        reminder.last_attempt_at = _now()
        if not active:
            reminder.status = "skipped"
            reminder.last_error = reason
            counts["skipped"] += 1
            record_event(
                session,
                action=audit_events.REMINDER_SKIPPED,
                resource_type="reminder_record",
                resource_id=reminder.id,
                organisation_id=reminder.organisation_id,
                actor_user_id=None,
                outcome=AuditOutcome.SUCCESS.value,
                summary="Reminder skipped — resource no longer actionable",
                metadata={"reason": reason, "kind": reminder.reminder_kind},
            )
            continue
        message = ReminderMessage(
            organisation_id=str(reminder.organisation_id),
            recipient_user_id=str(reminder.recipient_user_id),
            subject=reminder.payload_summary or reminder.reminder_kind,
            body=reminder.payload_summary or reminder.reminder_kind,
            channel=reminder.channel,
        )
        try:
            result = provider.send(message)
            if result.success:
                reminder.status = "sent"
                reminder.delivered = True
                reminder.last_error = None
                counts["sent"] += 1
                if (
                    reminder.resource_type == "safeguarding_reminder"
                    and reminder.reminder_kind == "safeguarding_upcoming"
                ):
                    sg = session.get(SafeguardingReminder, reminder.resource_id)
                    if sg is not None and sg.status == "pending":
                        sg.status = "sent"
                record_event(
                    session,
                    action=audit_events.REMINDER_SENT,
                    resource_type="reminder_record",
                    resource_id=reminder.id,
                    organisation_id=reminder.organisation_id,
                    actor_user_id=None,
                    outcome=AuditOutcome.SUCCESS.value,
                    summary="Reminder delivered via foundation provider",
                    metadata={"provider": result.provider, "detail": result.detail},
                )
            else:
                reminder.status = "failed"
                reminder.last_error = result.detail
                counts["failed"] += 1
                record_event(
                    session,
                    action=audit_events.REMINDER_FAILED,
                    resource_type="reminder_record",
                    resource_id=reminder.id,
                    organisation_id=reminder.organisation_id,
                    actor_user_id=None,
                    outcome=AuditOutcome.FAILURE.value,
                    summary="Reminder delivery failed",
                    metadata={"provider": result.provider, "detail": result.detail},
                )
        except Exception as exc:  # noqa: BLE001 — worker must record failure
            logger.exception("reminder_dispatch_error id=%s", reminder.id)
            reminder.status = "failed"
            reminder.last_error = str(exc)[:2000]
            counts["failed"] += 1
    session.flush()
    return counts


def dispatch_org_reminders(session: Session, payload: dict) -> dict[str, int]:
    """Validate org job context then dispatch due reminders for that organisation only."""
    apply_platform_rls_bypass(session)
    ctx = validate_job_organisation_context(session, payload, require_actor=False)
    apply_organisation_rls(session, ctx.organisation_id)
    settings = get_settings()
    due = list(
        session.scalars(
            select(ReminderRecord)
            .where(
                ReminderRecord.organisation_id == ctx.organisation_id,
                ReminderRecord.status == "pending",
                ReminderRecord.scheduled_for <= _now(),
            )
            .order_by(ReminderRecord.scheduled_for.asc())
            .limit(settings.reminder_dispatch_batch_size)
        ).all()
    )
    # Reuse per-row logic by temporarily marking others out of scope — process listed ids.
    ids = {row.id for row in due}
    # Process using shared helper path: set non-matching pending far future? Simpler: inline loop.
    provider = get_notification_provider()
    counts = {"sent": 0, "failed": 0, "skipped": 0, "processed": 0}
    for reminder in due:
        counts["processed"] += 1
        active, reason = _resource_still_active(session, reminder)
        reminder.attempt_count += 1
        reminder.last_attempt_at = _now()
        if not active:
            reminder.status = "skipped"
            reminder.last_error = reason
            counts["skipped"] += 1
            continue
        result = provider.send(
            ReminderMessage(
                organisation_id=str(reminder.organisation_id),
                recipient_user_id=str(reminder.recipient_user_id),
                subject=reminder.payload_summary or reminder.reminder_kind,
                body=reminder.payload_summary or reminder.reminder_kind,
                channel=reminder.channel,
            )
        )
        if result.success:
            reminder.status = "sent"
            reminder.delivered = True
            counts["sent"] += 1
        else:
            reminder.status = "failed"
            reminder.last_error = result.detail
            counts["failed"] += 1
    session.flush()
    return counts
