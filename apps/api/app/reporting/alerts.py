"""Early-warning operational alerts (F6.2) — not the F6.3 automation rules engine."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.complaints import Complaint
from app.db.models.enums import RecordStatus
from app.db.models.housing import HousingApplication
from app.db.models.reporting_analytics import EarlyWarningAlert, EarlyWarningThreshold
from app.db.models.room import Room
from app.db.models.support_ops import CaseAssignment
from app.db.models.support_plans import TenantSupportPlan
from app.db.models.tenant import Tenant
from app.db.models.tenant_timeline import TenantFollowUp
from app.reporting.access import require_alerts_view, require_schedule_manage
from app.reporting.complaints_reports import OPEN_STATUSES
from app.tenancy.context import OrganisationContext

DEFAULT_THRESHOLDS: dict[str, int] = {
    "overdue_complaints": 5,
    "pending_housing": 20,
    "overdue_followups": 10,
    "overdue_plan_reviews": 5,
    "occupancy_drop": 50,  # occupancy rate % below this triggers when rooms exist
    "high_caseload": 25,  # active assignments per worker
}

OPEN_FOLLOWUP = ("open", "in_progress", "awaiting_information")
PENDING_HOUSING = ("submitted", "under_review", "information_required")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _threshold_map(session: Session, organisation_id: uuid.UUID) -> dict[str, int]:
    rows = session.scalars(
        select(EarlyWarningThreshold).where(
            EarlyWarningThreshold.organisation_id == organisation_id,
            EarlyWarningThreshold.is_enabled.is_(True),
        )
    ).all()
    merged = dict(DEFAULT_THRESHOLDS)
    for row in rows:
        merged[row.alert_type] = int(row.threshold_value)
    return merged


def upsert_threshold(
    session: Session,
    ctx: OrganisationContext,
    *,
    alert_type: str,
    threshold_value: int,
    is_enabled: bool = True,
) -> dict[str, Any]:
    require_schedule_manage(ctx)
    if alert_type not in DEFAULT_THRESHOLDS:
        raise HTTPException(status_code=400, detail="Unknown alert type")
    if threshold_value < 0:
        raise HTTPException(status_code=400, detail="threshold_value must be >= 0")
    row = session.scalar(
        select(EarlyWarningThreshold).where(
            EarlyWarningThreshold.organisation_id == ctx.organisation_id,
            EarlyWarningThreshold.alert_type == alert_type,
        )
    )
    if row is None:
        row = EarlyWarningThreshold(
            organisation_id=ctx.organisation_id,
            alert_type=alert_type,
            threshold_value=threshold_value,
            is_enabled=is_enabled,
            updated_by_user_id=ctx.user_id,
        )
        session.add(row)
    else:
        row.threshold_value = threshold_value
        row.is_enabled = is_enabled
        row.updated_by_user_id = ctx.user_id
    session.flush()
    return {
        "alert_type": row.alert_type,
        "threshold_value": row.threshold_value,
        "is_enabled": row.is_enabled,
    }


def list_thresholds(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_alerts_view(ctx)
    configured = {
        r.alert_type: r
        for r in session.scalars(
            select(EarlyWarningThreshold).where(
                EarlyWarningThreshold.organisation_id == ctx.organisation_id
            )
        ).all()
    }
    out = []
    for alert_type, default in DEFAULT_THRESHOLDS.items():
        row = configured.get(alert_type)
        out.append(
            {
                "alert_type": alert_type,
                "threshold_value": row.threshold_value if row else default,
                "is_enabled": row.is_enabled if row else True,
                "is_default": row is None,
            }
        )
    return out


def _upsert_alert(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    alert_type: str,
    title: str,
    reason: str,
    metric_value: int,
    threshold_value: int,
    related_refs: dict[str, Any],
    dedupe_key: str,
    severity: str = "warning",
) -> EarlyWarningAlert | None:
    existing = session.scalar(
        select(EarlyWarningAlert).where(
            EarlyWarningAlert.organisation_id == organisation_id,
            EarlyWarningAlert.dedupe_key == dedupe_key,
        )
    )
    if existing is not None:
        if existing.status in ("open", "acknowledged"):
            existing.metric_value = metric_value
            existing.reason = reason
            existing.related_refs = related_refs
            session.flush()
            return None  # duplicate prevented
        # Previously resolved — reopen with same dedupe key only if still breached
        existing.status = "open"
        existing.metric_value = metric_value
        existing.reason = reason
        existing.related_refs = related_refs
        existing.resolved_at = None
        session.flush()
        return existing
    row = EarlyWarningAlert(
        organisation_id=organisation_id,
        alert_type=alert_type,
        severity=severity,
        status="open",
        title=title,
        reason=reason,
        metric_value=metric_value,
        threshold_value=threshold_value,
        related_refs=related_refs,
        dedupe_key=dedupe_key,
    )
    session.add(row)
    session.flush()
    return row


def evaluate_organisation_alerts(session: Session, organisation_id: uuid.UUID) -> dict[str, Any]:
    """Generate early-warning alerts from live operational records."""
    thresholds = _threshold_map(session, organisation_id)
    created = 0
    updated = 0
    now = _now()
    today = date.today()
    day_key = today.isoformat()

    overdue_complaints = int(
        session.scalar(
            select(func.count()).select_from(Complaint).where(
                Complaint.organisation_id == organisation_id,
                Complaint.status.in_(tuple(OPEN_STATUSES)),
                Complaint.response_due_at.is_not(None),
                Complaint.response_due_at < now,
            )
        )
        or 0
    )
    th = thresholds["overdue_complaints"]
    if overdue_complaints >= th:
        row = _upsert_alert(
            session,
            organisation_id=organisation_id,
            alert_type="overdue_complaints",
            title="Increase in overdue complaints",
            reason=f"{overdue_complaints} open complaints are past response_due_at (threshold {th}).",
            metric_value=overdue_complaints,
            threshold_value=th,
            related_refs={"count": overdue_complaints},
            dedupe_key=f"overdue_complaints:{day_key}",
            severity="critical" if overdue_complaints >= th * 2 else "warning",
        )
        created += 1 if row else 0
        updated += 0 if row else 1

    pending_housing = int(
        session.scalar(
            select(func.count()).select_from(HousingApplication).where(
                HousingApplication.organisation_id == organisation_id,
                HousingApplication.status.in_(PENDING_HOUSING),
            )
        )
        or 0
    )
    th = thresholds["pending_housing"]
    if pending_housing >= th:
        row = _upsert_alert(
            session,
            organisation_id=organisation_id,
            alert_type="pending_housing",
            title="High number of pending housing applications",
            reason=f"{pending_housing} applications await processing (threshold {th}).",
            metric_value=pending_housing,
            threshold_value=th,
            related_refs={"count": pending_housing, "statuses": list(PENDING_HOUSING)},
            dedupe_key=f"pending_housing:{day_key}",
        )
        created += 1 if row else 0
        updated += 0 if row else 1

    overdue_fu = int(
        session.scalar(
            select(func.count()).select_from(TenantFollowUp).where(
                TenantFollowUp.organisation_id == organisation_id,
                TenantFollowUp.status.in_(OPEN_FOLLOWUP),
                TenantFollowUp.due_at.is_not(None),
                TenantFollowUp.due_at < now,
            )
        )
        or 0
    )
    th = thresholds["overdue_followups"]
    if overdue_fu >= th:
        row = _upsert_alert(
            session,
            organisation_id=organisation_id,
            alert_type="overdue_followups",
            title="Increasing overdue follow-up tasks",
            reason=f"{overdue_fu} open follow-ups are past due (threshold {th}).",
            metric_value=overdue_fu,
            threshold_value=th,
            related_refs={"count": overdue_fu},
            dedupe_key=f"overdue_followups:{day_key}",
        )
        created += 1 if row else 0
        updated += 0 if row else 1

    overdue_plans = int(
        session.scalar(
            select(func.count()).select_from(TenantSupportPlan).where(
                TenantSupportPlan.organisation_id == organisation_id,
                TenantSupportPlan.status.in_(("active", "under_review")),
                TenantSupportPlan.planned_review_date.is_not(None),
                TenantSupportPlan.planned_review_date < today,
            )
        )
        or 0
    )
    th = thresholds["overdue_plan_reviews"]
    if overdue_plans >= th:
        row = _upsert_alert(
            session,
            organisation_id=organisation_id,
            alert_type="overdue_plan_reviews",
            title="Support plans with overdue reviews",
            reason=f"{overdue_plans} active plans have planned_review_date before today (threshold {th}).",
            metric_value=overdue_plans,
            threshold_value=th,
            related_refs={"count": overdue_plans},
            dedupe_key=f"overdue_plan_reviews:{day_key}",
        )
        created += 1 if row else 0
        updated += 0 if row else 1

    # Occupancy: org-wide rate from active rooms / assigned tenants
    rooms = list(
        session.scalars(
            select(Room).where(
                Room.organisation_id == organisation_id,
                Room.status == RecordStatus.ACTIVE,
            )
        ).all()
    )
    if rooms:
        tenants = list(
            session.scalars(
                select(Tenant).where(
                    Tenant.organisation_id == organisation_id,
                    Tenant.status == RecordStatus.ACTIVE,
                    Tenant.assigned_room_id.is_not(None),
                )
            ).all()
        )
        occupied_ids = {t.assigned_room_id for t in tenants}
        occupied = sum(1 for r in rooms if r.id in occupied_ids)
        rate = int(round((occupied / len(rooms)) * 100))
        th = thresholds["occupancy_drop"]
        if rate <= th:
            row = _upsert_alert(
                session,
                organisation_id=organisation_id,
                alert_type="occupancy_drop",
                title="Significant change in property occupancy",
                reason=f"Organisation occupancy rate is {rate}% ({occupied}/{len(rooms)} rooms; threshold {th}%).",
                metric_value=rate,
                threshold_value=th,
                related_refs={"occupied_rooms": occupied, "total_rooms": len(rooms), "rate": rate},
                dedupe_key=f"occupancy_drop:{day_key}",
            )
            created += 1 if row else 0
            updated += 0 if row else 1

    # High caseload per worker
    th = thresholds["high_caseload"]
    worker_counts = session.execute(
        select(CaseAssignment.support_worker_user_id, func.count())
        .where(
            CaseAssignment.organisation_id == organisation_id,
            CaseAssignment.status == "active",
        )
        .group_by(CaseAssignment.support_worker_user_id)
    ).all()
    overloaded = [
        {"support_worker_user_id": str(uid), "active_cases": int(cnt)}
        for uid, cnt in worker_counts
        if uid is not None and int(cnt) >= th
    ]
    if overloaded:
        max_load = max(x["active_cases"] for x in overloaded)
        row = _upsert_alert(
            session,
            organisation_id=organisation_id,
            alert_type="high_caseload",
            title="High staff caseloads",
            reason=f"{len(overloaded)} support worker(s) at or above {th} active assignments (max {max_load}).",
            metric_value=max_load,
            threshold_value=th,
            related_refs={"workers": overloaded[:20]},
            dedupe_key=f"high_caseload:{day_key}",
            severity="critical" if max_load >= th * 2 else "warning",
        )
        created += 1 if row else 0
        updated += 0 if row else 1

    return {
        "organisation_id": str(organisation_id),
        "created": created,
        "refreshed": updated,
        "evaluated_at": now.isoformat(),
    }


def list_alerts(
    session: Session,
    ctx: OrganisationContext,
    *,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    require_alerts_view(ctx)
    stmt = select(EarlyWarningAlert).where(EarlyWarningAlert.organisation_id == ctx.organisation_id)
    if status_filter:
        stmt = stmt.where(EarlyWarningAlert.status == status_filter)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * page_size
    rows = session.scalars(
        stmt.order_by(EarlyWarningAlert.created_at.desc()).offset(offset).limit(page_size)
    ).all()
    return {
        "items": [alert_to_dict(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": int(total),
    }


def update_alert_status(
    session: Session,
    ctx: OrganisationContext,
    alert_id: uuid.UUID,
    *,
    new_status: str,
) -> dict[str, Any]:
    require_alerts_view(ctx)
    if new_status not in ("acknowledged", "resolved", "dismissed", "open"):
        raise HTTPException(status_code=400, detail="Invalid status")
    row = session.get(EarlyWarningAlert, alert_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    row.status = new_status
    if new_status == "acknowledged":
        row.acknowledged_at = _now()
        row.acknowledged_by_user_id = ctx.user_id
    if new_status in ("resolved", "dismissed"):
        row.resolved_at = _now()
    session.flush()
    record_event(
        session,
        action=audit_events.REPORTS_ALERT_STATUS,
        resource_type="early_warning_alert",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Alert status -> {new_status}",
        raise_on_error=False,
    )
    return alert_to_dict(row)


def alert_to_dict(row: EarlyWarningAlert) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "alert_type": row.alert_type,
        "severity": row.severity,
        "status": row.status,
        "title": row.title,
        "reason": row.reason,
        "metric_value": row.metric_value,
        "threshold_value": row.threshold_value,
        "related_refs": row.related_refs,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }
