"""Background deadline / escalation processing for F2.7 (Celery).

Uses organisation-scoped job context from F2.2. Escalation inserts are
idempotent via complaint_escalations.idempotency_key uniqueness.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.complaints.service import OPEN_STATUSES, is_overdue
from app.db.models.complaints import Complaint, ComplaintDeadlineRule, ComplaintEscalation, ComplaintStatusHistory
from app.db.models.organisation import Organisation
from app.tenancy.jobs import validate_job_organisation_context
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

logger = logging.getLogger("hmore.complaints.jobs")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def process_overdue_escalations_for_org(session: Session, organisation_id: uuid.UUID) -> dict:
    """Create overdue escalations for an organisation. Idempotent per due-day key."""
    apply_organisation_rls(session, organisation_id)
    now = _now()
    created = 0
    skipped = 0
    failures = 0

    rows = list(
        session.scalars(
            select(Complaint).where(
                Complaint.organisation_id == organisation_id,
                Complaint.status.in_(tuple(OPEN_STATUSES)),
            )
        ).all()
    )
    for complaint in rows:
        if not is_overdue(complaint, now):
            continue
        rule = session.scalar(
            select(ComplaintDeadlineRule).where(
                ComplaintDeadlineRule.organisation_id == organisation_id,
                ComplaintDeadlineRule.priority == complaint.priority,
            )
        )
        if rule is not None and not rule.auto_escalate_overdue:
            skipped += 1
            continue
        due_day = (complaint.response_due_at or complaint.acknowledge_due_at or now).date().isoformat()
        key = f"overdue:{due_day}"
        existing = session.scalar(
            select(ComplaintEscalation).where(
                ComplaintEscalation.complaint_id == complaint.id,
                ComplaintEscalation.idempotency_key == key,
            )
        )
        if existing is not None:
            skipped += 1
            continue
        try:
            with session.begin_nested():
                esc = ComplaintEscalation(
                    organisation_id=organisation_id,
                    complaint_id=complaint.id,
                    idempotency_key=key,
                    reason="Automatic escalation: operational response deadline overdue",
                    escalated_by_user_id=None,
                    recipient_role="organisation_admin",
                    previous_assigned_user_id=complaint.assigned_user_id,
                    status="open",
                    escalated_at=now,
                )
                session.add(esc)
                if complaint.status != "escalated":
                    prev = complaint.status
                    complaint.status = "escalated"
                    session.add(
                        ComplaintStatusHistory(
                            organisation_id=organisation_id,
                            complaint_id=complaint.id,
                            from_status=prev,
                            to_status="escalated",
                            changed_by_user_id=None,
                            note="Auto-escalated after operational deadline",
                        )
                    )
                session.flush()
            created += 1
        except IntegrityError:
            skipped += 1
            logger.info(
                "Duplicate overdue escalation skipped complaint_id=%s key=%s",
                complaint.id,
                key,
            )
        except Exception:
            failures += 1
            logger.exception("Failed overdue escalation for complaint_id=%s", complaint.id)

    record_event(
        session,
        action=audit_events.COMPLAINT_OVERDUE_SCAN,
        resource_type="organisation",
        resource_id=organisation_id,
        organisation_id=organisation_id,
        actor_user_id=None,
        actor_role="system",
        outcome=AuditOutcome.SUCCESS.value,
        summary="Complaint overdue escalation scan completed",
        metadata={"created": created, "skipped": skipped, "failures": failures},
        raise_on_error=False,
    )
    return {
        "organisation_id": str(organisation_id),
        "created": created,
        "skipped": skipped,
        "failures": failures,
    }


def dispatch_overdue_escalations(session: Session) -> dict:
    """Platform job: scan all organisations for overdue complaint escalations."""
    apply_platform_rls_bypass(session)
    org_ids = list(session.scalars(select(Organisation.id)).all())
    totals = {"organisations": 0, "created": 0, "skipped": 0, "failures": 0}
    for org_id in org_ids:
        result = process_overdue_escalations_for_org(session, org_id)
        totals["organisations"] += 1
        totals["created"] += result["created"]
        totals["skipped"] += result["skipped"]
        totals["failures"] += result["failures"]
    logger.info("dispatch_overdue_escalations result=%s", totals)
    return totals


def dispatch_org_overdue_escalations(session: Session, payload: dict) -> dict:
    ctx = validate_job_organisation_context(session, payload, require_actor=False)
    return process_overdue_escalations_for_org(session, ctx.organisation_id)
