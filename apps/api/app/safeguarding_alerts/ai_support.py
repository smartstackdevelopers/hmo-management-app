"""F8.2 AI-assisted safeguarding support — suggestions only, no risk conclusions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.compliance import SafeguardingReminder
from app.db.models.support_ops import DailyLog
from app.db.models.incidents import Incident
from app.safeguarding_alerts.constants import RULE_TRIGGER_TYPES

UNCERTAINTY = (
    "This is an AI-generated draft for human review only. "
    "It does not determine risk, abuse, neglect, or safety outcomes."
)

REVIEW_QUESTIONS = [
    "What recent staff notes relate to this concern?",
    "Who last had contact with the tenant?",
    "Is a follow-up already scheduled?",
    "Are any incidents or complaints still open?",
]


def build_case_summary_draft(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Organise existing records — no unsupported accusations."""
    incident_count = int(
        session.scalar(
            select(func.count())
            .select_from(Incident)
            .where(Incident.organisation_id == organisation_id, Incident.tenant_id == tenant_id)
        )
        or 0
    )
    note_count = int(
        session.scalar(
            select(func.count())
            .select_from(DailyLog)
            .where(DailyLog.organisation_id == organisation_id, DailyLog.tenant_id == tenant_id)
        )
        or 0
    )
    overdue_reminders = int(
        session.scalar(
            select(func.count())
            .select_from(SafeguardingReminder)
            .where(
                SafeguardingReminder.organisation_id == organisation_id,
                SafeguardingReminder.tenant_id == tenant_id,
                SafeguardingReminder.status == "overdue",
            )
        )
        or 0
    )
    lines = [
        f"Recorded incidents for review: {incident_count} (human verification required).",
        f"Daily support log entries on file: {note_count}.",
        f"Overdue safeguarding reminder records: {overdue_reminders}.",
        "Suggested human review questions:",
    ]
    lines.extend(f"- {q}" for q in REVIEW_QUESTIONS)
    source_refs = [
        {"type": "incidents", "count": incident_count},
        {"type": "daily_logs", "count": note_count},
        {"type": "safeguarding_reminders_overdue", "count": overdue_reminders},
    ]
    return {
        "suggestion_type": "case_summary_draft",
        "content": "\n".join(lines),
        "source_refs": source_refs,
        "uncertainty_note": UNCERTAINTY,
        "requires_human_review": True,
    }


def allowed_trigger_types() -> frozenset[str]:
    return RULE_TRIGGER_TYPES
