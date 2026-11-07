"""Deterministic compliance rules sourced from existing HMore business logic.

These rules reuse operational deadlines and expiry fields already defined in
F2.3, F2.4, F2.7, F2.10, and F2.11. They do not invent legislation or statutory
thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.complaints.service import OPEN_STATUSES, is_overdue
from app.db.models.compliance import SafeguardingReminder, StaffTrainingRecord
from app.db.models.complaints import Complaint
from app.db.models.incidents import IncidentFollowUp
from app.db.models.managed_documents import ManagedDocument
from app.db.models.support_plans import TenantSupportPlan


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    version: str
    name: str
    description: str
    source: str
    module: str
    record_type: str
    severity: str = "normal"


@dataclass
class RuleHit:
    rule: RuleDefinition
    source_record_id: UUID
    result: str
    title: str
    detail: str
    due_date: date | None
    evidence_refs: list[dict[str, Any]]
    severity: str


NOTICE = (
    "AI assistance only — this sweep does not provide legal certification or an "
    "autonomous compliance decision. Final decisions remain with authorised human staff."
)


def list_rules() -> list[RuleDefinition]:
    return list(RULE_CATALOG)


def get_rule(rule_id: str) -> RuleDefinition | None:
    for rule in RULE_CATALOG:
        if rule.rule_id == rule_id:
            return rule
    return None


def heuristic_explanation(hits: list[RuleHit]) -> str:
    by_module: dict[str, int] = {}
    for hit in hits:
        by_module[hit.rule.module] = by_module.get(hit.rule.module, 0) + 1
    parts = [f"{module}: {count}" for module, count in sorted(by_module.items())]
    summary = "; ".join(parts) if parts else "No potential gaps from configured HMore rules."
    return (
        f"{NOTICE} Rule-based potential gaps: {len(hits)}. "
        f"By module — {summary}. Staff should verify each finding against the source record."
    )


def validate_ai_explanation(text: str) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) < 20:
        raise ValueError("AI explanation too short")
    lowered = cleaned.lower()
    banned = (
        "legally compliant",
        "legally non-compliant",
        "certified compliant",
        "statutory breach",
        "regulatory violation confirmed",
        "automatically resolved",
    )
    for phrase in banned:
        if phrase in lowered:
            raise ValueError("AI explanation asserts a prohibited compliance decision")
    return cleaned[:4000]


RULE_CATALOG: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        rule_id="training.expired",
        version="1.0.0",
        name="Staff training expiry",
        description="Flags staff training records whose recorded expiry_date is before today.",
        source="hmore.f23.staff_training_records.expiry_date",
        module="training",
        record_type="staff_training_record",
        severity="high",
    ),
    RuleDefinition(
        rule_id="safeguarding.overdue",
        version="1.0.0",
        name="Safeguarding reminder overdue",
        description="Flags safeguarding reminders marked overdue or past due_at while still open.",
        source="hmore.f23.safeguarding_reminders.due_at_status",
        module="safeguarding",
        record_type="safeguarding_reminder",
        severity="high",
    ),
    RuleDefinition(
        rule_id="incident.follow_up_overdue",
        version="1.0.0",
        name="Incident follow-up overdue",
        description="Flags open incident follow-ups whose due_at is in the past.",
        source="hmore.f24.incident_follow_ups.due_at",
        module="incidents",
        record_type="incident_follow_up",
        severity="high",
    ),
    RuleDefinition(
        rule_id="support_plan.review_overdue",
        version="1.0.0",
        name="Support plan review overdue",
        description="Flags active support plans whose planned_review_date is before today.",
        source="hmore.f210.tenant_support_plans.planned_review_date",
        module="support_plans",
        record_type="tenant_support_plan",
        severity="normal",
    ),
    RuleDefinition(
        rule_id="document.expired",
        version="1.0.0",
        name="Managed document expired",
        description="Flags managed documents with expiry_tracking=expired or expiry_date before today.",
        source="hmore.f211.managed_documents.expiry",
        module="documents",
        record_type="managed_document",
        severity="normal",
    ),
    RuleDefinition(
        rule_id="complaint.response_overdue",
        version="1.0.0",
        name="Complaint response overdue",
        description="Flags open complaints past acknowledge or response deadlines (F2.7 is_overdue).",
        source="hmore.f27.complaints.is_overdue",
        module="complaints",
        record_type="complaint",
        severity="high",
    ),
)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _eval_training(session: Session, organisation_id: UUID) -> tuple[int, list[RuleHit]]:
    rule = get_rule("training.expired")
    assert rule is not None
    rows = list(
        session.scalars(
            select(StaffTrainingRecord).where(
                StaffTrainingRecord.organisation_id == organisation_id,
                StaffTrainingRecord.status != "exempt",
            )
        )
    )
    hits: list[RuleHit] = []
    today = _today()
    for row in rows:
        if row.expiry_date is None:
            continue
        if row.expiry_date >= today:
            continue
        hits.append(
            RuleHit(
                rule=rule,
                source_record_id=row.id,
                result="potential_gap",
                title=f"Training expired: {row.title}",
                detail=(
                    f"Staff training record expiry_date {row.expiry_date.isoformat()} is before today. "
                    "Source: organisation training record (F2.3). Not a legal determination."
                ),
                due_date=row.expiry_date,
                evidence_refs=[
                    {
                        "type": "staff_training_record",
                        "id": str(row.id),
                        "field": "expiry_date",
                        "value": row.expiry_date.isoformat(),
                    }
                ],
                severity=rule.severity,
            )
        )
    return len(rows), hits


def _eval_safeguarding(session: Session, organisation_id: UUID) -> tuple[int, list[RuleHit]]:
    rule = get_rule("safeguarding.overdue")
    assert rule is not None
    rows = list(
        session.scalars(
            select(SafeguardingReminder).where(
                SafeguardingReminder.organisation_id == organisation_id,
                SafeguardingReminder.status.notin_(("completed", "cancelled")),
            )
        )
    )
    hits: list[RuleHit] = []
    now = _now()
    for row in rows:
        overdue = row.status == "overdue" or row.due_at < now
        if not overdue:
            continue
        hits.append(
            RuleHit(
                rule=rule,
                source_record_id=row.id,
                result="potential_gap",
                title=f"Safeguarding reminder overdue: {row.title}",
                detail=(
                    f"Reminder due_at {row.due_at.isoformat()} with status {row.status}. "
                    "Source: F2.3 safeguarding reminder workflow."
                ),
                due_date=row.due_at.date(),
                evidence_refs=[
                    {
                        "type": "safeguarding_reminder",
                        "id": str(row.id),
                        "field": "due_at",
                        "value": row.due_at.isoformat(),
                        "status": row.status,
                    }
                ],
                severity=rule.severity,
            )
        )
    return len(rows), hits


def _eval_incident_follow_ups(session: Session, organisation_id: UUID) -> tuple[int, list[RuleHit]]:
    rule = get_rule("incident.follow_up_overdue")
    assert rule is not None
    rows = list(
        session.scalars(
            select(IncidentFollowUp).where(
                IncidentFollowUp.organisation_id == organisation_id,
                IncidentFollowUp.status.in_(("open", "in_progress", "blocked")),
            )
        )
    )
    hits: list[RuleHit] = []
    now = _now()
    for row in rows:
        if row.due_at is None or row.due_at >= now:
            continue
        hits.append(
            RuleHit(
                rule=rule,
                source_record_id=row.id,
                result="potential_gap",
                title="Incident follow-up overdue",
                detail=(
                    f"Follow-up due_at {row.due_at.isoformat()} is past and status is {row.status}. "
                    "Source: F2.4 incident follow-up reminders."
                ),
                due_date=row.due_at.date(),
                evidence_refs=[
                    {
                        "type": "incident_follow_up",
                        "id": str(row.id),
                        "incident_id": str(row.incident_id),
                        "field": "due_at",
                        "value": row.due_at.isoformat(),
                    }
                ],
                severity=rule.severity,
            )
        )
    return len(rows), hits


def _eval_support_plan_reviews(session: Session, organisation_id: UUID) -> tuple[int, list[RuleHit]]:
    rule = get_rule("support_plan.review_overdue")
    assert rule is not None
    rows = list(
        session.scalars(
            select(TenantSupportPlan).where(
                TenantSupportPlan.organisation_id == organisation_id,
                TenantSupportPlan.status.in_(("active", "under_review", "on_hold")),
            )
        )
    )
    hits: list[RuleHit] = []
    today = _today()
    for row in rows:
        if row.planned_review_date is None:
            continue
        if row.planned_review_date >= today:
            continue
        hits.append(
            RuleHit(
                rule=rule,
                source_record_id=row.id,
                result="potential_gap",
                title="Support plan review overdue",
                detail=(
                    f"planned_review_date {row.planned_review_date.isoformat()} is before today "
                    f"for plan status {row.status}. Source: F2.10 support-plan progress metrics."
                ),
                due_date=row.planned_review_date,
                evidence_refs=[
                    {
                        "type": "tenant_support_plan",
                        "id": str(row.id),
                        "field": "planned_review_date",
                        "value": row.planned_review_date.isoformat(),
                    }
                ],
                severity=rule.severity,
            )
        )
    return len(rows), hits


def _eval_documents(session: Session, organisation_id: UUID) -> tuple[int, list[RuleHit]]:
    rule = get_rule("document.expired")
    assert rule is not None
    rows = list(
        session.scalars(
            select(ManagedDocument).where(ManagedDocument.organisation_id == organisation_id)
        )
    )
    hits: list[RuleHit] = []
    today = _today()
    for row in rows:
        expired = row.expiry_tracking == "expired" or (
            row.expiry_date is not None and row.expiry_date < today
        )
        if not expired:
            continue
        hits.append(
            RuleHit(
                rule=rule,
                source_record_id=row.id,
                result="potential_gap",
                title=f"Document expired: {row.title}",
                detail=(
                    f"Managed document expiry_tracking={row.expiry_tracking}; "
                    f"expiry_date={row.expiry_date.isoformat() if row.expiry_date else 'null'}. "
                    "Source: F2.11 document expiry tracking."
                ),
                due_date=row.expiry_date,
                evidence_refs=[
                    {
                        "type": "managed_document",
                        "id": str(row.id),
                        "field": "expiry_date",
                        "value": row.expiry_date.isoformat() if row.expiry_date else None,
                        "expiry_tracking": row.expiry_tracking,
                    }
                ],
                severity=rule.severity,
            )
        )
    return len(rows), hits


def _eval_complaints(session: Session, organisation_id: UUID) -> tuple[int, list[RuleHit]]:
    rule = get_rule("complaint.response_overdue")
    assert rule is not None
    rows = list(
        session.scalars(
            select(Complaint).where(
                Complaint.organisation_id == organisation_id,
                Complaint.status.in_(tuple(OPEN_STATUSES)),
            )
        )
    )
    hits: list[RuleHit] = []
    now = _now()
    for row in rows:
        if not is_overdue(row, now):
            continue
        hits.append(
            RuleHit(
                rule=rule,
                source_record_id=row.id,
                result="potential_gap",
                title="Complaint response overdue",
                detail=(
                    "Open complaint is past the organisation deadline rule (acknowledge/response). "
                    "Source: F2.7 complaints is_overdue helper."
                ),
                due_date=(row.response_due_at or row.acknowledge_due_at).date()
                if (row.response_due_at or row.acknowledge_due_at)
                else None,
                evidence_refs=[
                    {
                        "type": "complaint",
                        "id": str(row.id),
                        "status": row.status,
                        "response_due_at": row.response_due_at.isoformat() if row.response_due_at else None,
                        "acknowledge_due_at": row.acknowledge_due_at.isoformat()
                        if row.acknowledge_due_at
                        else None,
                    }
                ],
                severity=rule.severity,
            )
        )
    return len(rows), hits


_EVALUATORS: dict[str, Callable[[Session, UUID], tuple[int, list[RuleHit]]]] = {
    "training": _eval_training,
    "safeguarding": _eval_safeguarding,
    "incidents": _eval_incident_follow_ups,
    "support_plans": _eval_support_plan_reviews,
    "documents": _eval_documents,
    "complaints": _eval_complaints,
}


def evaluate_rules(
    session: Session,
    organisation_id: UUID,
    *,
    modules: list[str] | None = None,
) -> tuple[list[RuleDefinition], int, list[RuleHit]]:
    selected = modules or list(_EVALUATORS.keys())
    unknown = [m for m in selected if m not in _EVALUATORS]
    rules_run: list[RuleDefinition] = []
    hits: list[RuleHit] = []
    records = 0
    for module in selected:
        if module not in _EVALUATORS:
            continue
        for rule in RULE_CATALOG:
            if rule.module == module:
                rules_run.append(rule)
        count, module_hits = _EVALUATORS[module](session, organisation_id)
        records += count
        hits.extend(module_hits)
    if unknown:
        # Unconfigured / unknown modules are reported as unable to verify, not failures.
        for module in unknown:
            hits.append(
                RuleHit(
                    rule=RuleDefinition(
                        rule_id=f"unverifiable.{module}",
                        version="1.0.0",
                        name=f"Unconfigured module: {module}",
                        description="No verified HMore compliance rule is registered for this module.",
                        source="hmore.f39.rule_catalog",
                        module=module,
                        record_type="none",
                        severity="normal",
                    ),
                    source_record_id=organisation_id,
                    result="unable_to_verify",
                    title=f"Cannot verify module '{module}'",
                    detail="No verified HMore rule source exists for this module scope.",
                    due_date=None,
                    evidence_refs=[{"type": "module", "id": module}],
                    severity="normal",
                )
            )
    return rules_run, records, hits
