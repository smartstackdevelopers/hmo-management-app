"""Celery job: dispatch due CommunicationScheduledReminder rows (idempotent)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.communication import CommunicationScheduledReminder
from app.ops.notifications import CommunicationNotificationProvider, ReminderMessage
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

logger = logging.getLogger("hmore.communication.jobs")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def dispatch_due_communication_reminders(session: Session, *, limit: int = 100) -> dict[str, int]:
    apply_platform_rls_bypass(session)
    provider = CommunicationNotificationProvider()
    due = list(
        session.scalars(
            select(CommunicationScheduledReminder)
            .where(
                CommunicationScheduledReminder.status == "pending",
                CommunicationScheduledReminder.scheduled_at <= _now(),
            )
            .order_by(CommunicationScheduledReminder.scheduled_at.asc())
            .limit(limit)
        ).all()
    )
    counts = {"processed": 0, "sent": 0, "failed": 0}
    for row in due:
        counts["processed"] += 1
        apply_organisation_rls(session, row.organisation_id)
        result = provider.send(
            session,
            ReminderMessage(
                organisation_id=str(row.organisation_id),
                recipient_user_id=str(row.recipient_user_id),
                subject=row.subject or row.reminder_kind,
                body=row.body,
                channel=row.channel,
                target_type="communication_scheduled_reminder",
                target_id=str(row.id),
                idempotency_key=f"comm_reminder:{row.id}:{row.channel}",
                essential_operational=True,
            ),
        )
        if result.success:
            row.status = "sent"
            counts["sent"] += 1
        else:
            row.status = "failed"
            counts["failed"] += 1
        record_event(
            session,
            action=audit_events.COMMUNICATION_DELIVERY_DISPATCH,
            resource_type="communication_scheduled_reminder",
            resource_id=row.id,
            organisation_id=row.organisation_id,
            actor_user_id=None,
            outcome=AuditOutcome.SUCCESS.value if result.success else AuditOutcome.FAILURE.value,
            summary="Communication reminder dispatch",
            metadata={"provider": result.provider, "detail": result.detail},
            source="worker",
        )
    session.flush()
    return counts
