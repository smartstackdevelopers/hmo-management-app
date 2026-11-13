"""F8.2 configurable rule evaluation — thresholds from organisation config only."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.compliance import SafeguardingReminder
from app.db.models.complaints import Complaint
from app.db.models.incidents import Incident
from app.db.models.maintenance import MaintenanceRequest
from app.db.models.scheduling import OperationalTask, TenantVisit
from app.db.models.support_plans import TenantSupportPlan
from app.db.models.safeguarding_alerts import SafeguardingAlert, SafeguardingAlertRule


@dataclass(frozen=True)
class RuleHit:
    tenant_id: uuid.UUID
    rule: SafeguardingAlertRule
    description: str
    dedupe_key: str
    metadata: dict[str, Any]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _window_days(config: dict[str, Any]) -> int:
    raw = config.get("window_days", 30)
    try:
        return max(1, min(365, int(raw)))
    except (TypeError, ValueError):
        return 30


def _threshold(config: dict[str, Any], default: int = 2) -> int:
    raw = config.get("threshold", default)
    try:
        return max(1, min(100, int(raw)))
    except (TypeError, ValueError):
        return default


def evaluate_rule(session: Session, rule: SafeguardingAlertRule) -> list[RuleHit]:
    if not rule.enabled:
        return []
    cfg = rule.trigger_config or {}
    window = _now() - timedelta(days=_window_days(cfg))
    org_id = rule.organisation_id
    hits: list[RuleHit] = []
    tt = rule.trigger_type

    if tt == "repeated_missed_appointments":
        thr = _threshold(cfg, 2)
        rows = session.execute(
            select(TenantVisit.tenant_id, func.count())
            .where(
                TenantVisit.organisation_id == org_id,
                TenantVisit.status == "missed",
                TenantVisit.scheduled_at >= window,
                TenantVisit.tenant_id.is_not(None),
            )
            .group_by(TenantVisit.tenant_id)
            .having(func.count() >= thr)
        ).all()
        for tenant_id, count in rows:
            dedupe = f"rule:{rule.id}:tenant:{tenant_id}:missed_visits"
            hits.append(
                RuleHit(
                    tenant_id=tenant_id,
                    rule=rule,
                    description=(
                        f"Rule '{rule.name}': {count} missed visit(s) in the configured window "
                        "(requires human review)."
                    ),
                    dedupe_key=dedupe,
                    metadata={"missed_visits": int(count), "trigger_type": tt},
                )
            )

    elif tt == "multiple_unresolved_support_tasks":
        thr = _threshold(cfg, 3)
        open_status = ("open", "in_progress", "blocked")
        rows = session.execute(
            select(OperationalTask.tenant_id, func.count())
            .where(
                OperationalTask.organisation_id == org_id,
                OperationalTask.status.in_(open_status),
                OperationalTask.tenant_id.is_not(None),
            )
            .group_by(OperationalTask.tenant_id)
            .having(func.count() >= thr)
        ).all()
        for tenant_id, count in rows:
            dedupe = f"rule:{rule.id}:tenant:{tenant_id}:open_tasks"
            hits.append(
                RuleHit(
                    tenant_id=tenant_id,
                    rule=rule,
                    description=f"Rule '{rule.name}': {count} unresolved support task(s) on record.",
                    dedupe_key=dedupe,
                    metadata={"open_tasks": int(count), "trigger_type": tt},
                )
            )

    elif tt == "repeated_reported_incidents":
        thr = _threshold(cfg, 2)
        rows = session.execute(
            select(Incident.tenant_id, func.count())
            .where(
                Incident.organisation_id == org_id,
                Incident.tenant_id.is_not(None),
                Incident.occurred_at >= window,
            )
            .group_by(Incident.tenant_id)
            .having(func.count() >= thr)
        ).all()
        for tenant_id, count in rows:
            dedupe = f"rule:{rule.id}:tenant:{tenant_id}:incidents"
            hits.append(
                RuleHit(
                    tenant_id=tenant_id,
                    rule=rule,
                    description=f"Rule '{rule.name}': {count} incident report(s) in the configured window.",
                    dedupe_key=dedupe,
                    metadata={"incidents": int(count), "trigger_type": tt},
                )
            )

    elif tt == "overdue_safeguarding_followups":
        rows = session.scalars(
            select(SafeguardingReminder).where(
                SafeguardingReminder.organisation_id == org_id,
                SafeguardingReminder.status == "overdue",
                SafeguardingReminder.tenant_id.is_not(None),
            )
        ).all()
        for rem in rows:
            if rem.tenant_id is None:
                continue
            dedupe = f"rule:{rule.id}:tenant:{rem.tenant_id}:reminder:{rem.id}"
            hits.append(
                RuleHit(
                    tenant_id=rem.tenant_id,
                    rule=rule,
                    description=f"Rule '{rule.name}': overdue safeguarding follow-up reminder recorded.",
                    dedupe_key=dedupe,
                    metadata={"reminder_id": str(rem.id), "trigger_type": tt},
                )
            )

    elif tt == "repeated_welfare_concerns":
        thr = _threshold(cfg, 2)
        welfare_slugs = ("welfare_concerns", "self_reported_concerns")
        from app.db.models.safeguarding_alerts import SafeguardingAlertCategory

        cat_ids = session.scalars(
            select(SafeguardingAlertCategory.id).where(
                SafeguardingAlertCategory.organisation_id == org_id,
                SafeguardingAlertCategory.slug.in_(welfare_slugs),
            )
        ).all()
        if not cat_ids:
            return hits
        rows = session.execute(
            select(SafeguardingAlert.tenant_id, func.count())
            .where(
                SafeguardingAlert.organisation_id == org_id,
                SafeguardingAlert.tenant_id.is_not(None),
                SafeguardingAlert.category_id.in_(cat_ids),
                SafeguardingAlert.created_at >= window,
                SafeguardingAlert.status.notin_(("closed",)),
            )
            .group_by(SafeguardingAlert.tenant_id)
            .having(func.count() >= thr)
        ).all()
        for tenant_id, count in rows:
            dedupe = f"rule:{rule.id}:tenant:{tenant_id}:welfare_alerts"
            hits.append(
                RuleHit(
                    tenant_id=tenant_id,
                    rule=rule,
                    description=f"Rule '{rule.name}': {count} open welfare-related alert(s) recorded.",
                    dedupe_key=dedupe,
                    metadata={"welfare_alerts": int(count), "trigger_type": tt},
                )
            )

    elif tt == "unresolved_urgent_maintenance":
        urgent = ("urgent", "emergency")
        open_status = (
            "submitted",
            "acknowledged",
            "under_review",
            "awaiting_approval",
            "approved",
            "in_progress",
        )
        rows = session.scalars(
            select(MaintenanceRequest).where(
                MaintenanceRequest.organisation_id == org_id,
                MaintenanceRequest.priority.in_(urgent),
                MaintenanceRequest.status.in_(open_status),
                MaintenanceRequest.tenant_id.is_not(None),
            )
        ).all()
        for req in rows:
            if req.tenant_id is None:
                continue
            dedupe = f"rule:{rule.id}:tenant:{req.tenant_id}:maint:{req.id}"
            hits.append(
                RuleHit(
                    tenant_id=req.tenant_id,
                    rule=rule,
                    description=f"Rule '{rule.name}': urgent maintenance request still open.",
                    dedupe_key=dedupe,
                    metadata={"maintenance_request_id": str(req.id), "trigger_type": tt},
                )
            )

    elif tt == "support_plan_review_failures":
        today = _now().date()
        rows = session.scalars(
            select(TenantSupportPlan).where(
                TenantSupportPlan.organisation_id == org_id,
                TenantSupportPlan.status == "active",
                TenantSupportPlan.planned_review_date.is_not(None),
                TenantSupportPlan.planned_review_date < today,
            )
        ).all()
        for plan in rows:
            dedupe = f"rule:{rule.id}:tenant:{plan.tenant_id}:plan:{plan.id}"
            hits.append(
                RuleHit(
                    tenant_id=plan.tenant_id,
                    rule=rule,
                    description=f"Rule '{rule.name}': support plan review date passed without recorded completion.",
                    dedupe_key=dedupe,
                    metadata={"support_plan_id": str(plan.id), "trigger_type": tt},
                )
            )

    return hits


def evaluate_all_rules(session: Session, organisation_id: uuid.UUID) -> list[RuleHit]:
    rules = session.scalars(
        select(SafeguardingAlertRule).where(
            SafeguardingAlertRule.organisation_id == organisation_id,
            SafeguardingAlertRule.enabled.is_(True),
        )
    ).all()
    out: list[RuleHit] = []
    for rule in rules:
        out.extend(evaluate_rule(session, rule))
    return out
