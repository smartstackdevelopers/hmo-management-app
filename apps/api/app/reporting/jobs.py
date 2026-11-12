"""Celery-backed scheduled report execution and alert evaluation (F6.2)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.membership import OrganisationMembership
from app.db.models.organisation import Organisation
from app.db.models.reporting_analytics import ScheduledReport, ScheduledReportRun
from app.db.models.user import User
from app.ops.notifications import CommunicationNotificationProvider, ReminderMessage
from app.rbac.context import AuthorizationContext, MembershipView
from app.reporting import (
    caseload_reports,
    complaints_reports,
    dashboard,
    exports,
    housing_reports,
    occupancy_reports,
    plan_completion_reports,
)
from app.reporting import alerts as alert_service
from app.reporting import schedules as schedule_service
from app.reporting import secure_exports
from app.reporting.filters import (
    CaseloadReportFilters,
    ComplaintsReportFilters,
    HousingReportFilters,
    OccupancyReportFilters,
    PlanReportFilters,
)
from app.tenancy.context import OrganisationContext

logger = logging.getLogger("hmore.reporting.jobs")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _system_ctx(session: Session, organisation_id: uuid.UUID, actor_user_id: uuid.UUID | None) -> OrganisationContext:
    user = session.get(User, actor_user_id) if actor_user_id else None
    membership = None
    if user is not None:
        membership = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == organisation_id,
                OrganisationMembership.user_id == user.id,
                OrganisationMembership.status == MembershipStatus.ACTIVE,
            )
        )
    if user is None or membership is None:
        membership = session.scalar(
            select(OrganisationMembership).where(
                OrganisationMembership.organisation_id == organisation_id,
                OrganisationMembership.role == HMoreRole.ORGANISATION_ADMIN,
                OrganisationMembership.status == MembershipStatus.ACTIVE,
            )
        )
        if membership is None:
            raise RuntimeError(f"No organisation admin for scheduled reports in {organisation_id}")
        user = session.get(User, membership.user_id)
    assert user is not None and membership is not None
    role = membership.role
    return OrganisationContext(
        user=user,
        organisation_id=organisation_id,
        role=role,
        authorization=AuthorizationContext(
            user=user,
            memberships=[
                MembershipView(
                    membership_id=membership.id,
                    role=role,
                    organisation_id=organisation_id,
                    status=MembershipStatus.ACTIVE,
                )
            ],
            active_organisation_id=organisation_id,
            active_role=role,
        ),
    )


def _build_payload(
    session: Session,
    ctx: OrganisationContext,
    category: str,
    period_from: datetime,
    period_to: datetime,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], str]:
    if category == "housing":
        flt = HousingReportFilters(created_from=period_from, created_to=period_to, page=1, page_size=2000)
        summary = housing_reports.housing_summary(session, ctx, flt)
        items, _ = housing_reports.housing_rows(session, ctx, flt)
        headers = list(items[0].keys()) if items else ["reference_number", "status"]
        return summary, items, headers, "Housing applications report"
    if category == "complaints":
        flt = ComplaintsReportFilters(created_from=period_from, created_to=period_to, page=1, page_size=2000)
        summary = complaints_reports.complaints_summary(session, ctx, flt)
        items, _ = complaints_reports.complaints_rows(session, ctx, flt)
        headers = list(items[0].keys()) if items else ["reference_number", "status"]
        return summary, items, headers, "Complaints report"
    if category == "caseload":
        flt = CaseloadReportFilters(page=1, page_size=2000)
        summary = caseload_reports.caseload_summary(session, ctx, flt)
        items, _ = caseload_reports.caseload_rows(session, ctx, flt)
        headers = list(items[0].keys()) if items else ["tenant_id", "support_worker_user_id"]
        return summary, items, headers, "Caseload report"
    if category == "occupancy":
        flt = OccupancyReportFilters(page=1, page_size=2000)
        summary = occupancy_reports.occupancy_summary(session, ctx, flt)
        items, _ = occupancy_reports.occupancy_rows(session, ctx, flt)
        headers = list(items[0].keys()) if items else ["property_name", "room_label", "status"]
        return summary, items, headers, "Occupancy report"
    if category == "plans":
        flt = PlanReportFilters(created_from=period_from, created_to=period_to, page=1, page_size=2000)
        summary = plan_completion_reports.plan_completion_summary(session, ctx, flt)
        items, _ = plan_completion_reports.plan_completion_rows(session, ctx, flt)
        headers = list(items[0].keys()) if items else ["reference_number", "status"]
        return summary, items, headers, "Support plan completion report"
    summary = dashboard.main_dashboard(session, ctx, created_from=period_from, created_to=period_to)
    items = [{"section": k, "value": str(v)} for k, v in summary.items() if k != "generated_at"]
    headers = ["section", "value"]
    return summary, items, headers, "Operational dashboard report"


def _render_body(export_format: str, title: str, summary: dict[str, Any], headers: list[str], items: list[dict]) -> bytes:
    if export_format == "csv":
        return exports.rows_to_csv(headers, items)
    if export_format == "pdf":
        lines = [f"{h}: {it.get(h)}" for it in items[:40] for h in headers[:4]]
        return exports.summary_to_pdf(title, summary, lines)
    return exports.rows_to_xlsx(title[:31], headers, items)


def _notify_recipients(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    recipients: list[str],
    schedule_name: str,
    export_id: uuid.UUID,
    run_id: uuid.UUID,
) -> int:
    provider = CommunicationNotificationProvider()
    sent = 0
    for raw in recipients:
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
        if membership is None:
            logger.warning("Skipping unauthorised scheduled report recipient %s", raw)
            continue
        message = ReminderMessage(
            organisation_id=str(organisation_id),
            recipient_user_id=str(uid),
            subject=f"Scheduled report ready: {schedule_name}",
            body=(
                f"Your scheduled report '{schedule_name}' is ready. "
                f"Download id: {export_id}. Run id: {run_id}."
            ),
            channel="in_app",
            target_type="scheduled_report_run",
            target_id=str(run_id),
            idempotency_key=f"scheduled-report:{run_id}:{uid}",
            essential_operational=True,
        )
        result = provider.send(session, message)
        if result.success:
            sent += 1
    return sent


def execute_scheduled_report(session: Session, schedule_id: uuid.UUID, *, retry_run_id: uuid.UUID | None = None) -> dict[str, Any]:
    schedule = session.get(ScheduledReport, schedule_id)
    if schedule is None:
        return {"ok": False, "error": "schedule_not_found"}
    if not schedule.is_enabled and retry_run_id is None:
        return {"ok": False, "error": "schedule_disabled"}

    period_to = _now()
    period_from = period_to - timedelta(days=max(1, schedule.period_days))
    if retry_run_id:
        run = session.get(ScheduledReportRun, retry_run_id)
        if run is None or run.scheduled_report_id != schedule.id:
            return {"ok": False, "error": "run_not_found"}
        run.status = "running"
        run.attempt_count = int(run.attempt_count or 0) + 1
        run.started_at = _now()
        run.error_message = None
    else:
        run = ScheduledReportRun(
            organisation_id=schedule.organisation_id,
            scheduled_report_id=schedule.id,
            status="running",
            started_at=_now(),
            attempt_count=1,
            period_from=period_from,
            period_to=period_to,
        )
        session.add(run)
    session.flush()

    try:
        ctx = _system_ctx(session, schedule.organisation_id, schedule.created_by_user_id)
        summary, items, headers, title = _build_payload(
            session, ctx, schedule.report_category, period_from, period_to
        )
        body = _render_body(schedule.export_format, title, summary, headers, items)
        export = secure_exports.store_report_export(
            session,
            ctx,
            category=schedule.report_category,
            export_format=schedule.export_format,
            title=f"{schedule.name} ({title})",
            body=body,
            filters={
                "period_from": period_from.isoformat(),
                "period_to": period_to.isoformat(),
                "schedule_id": str(schedule.id),
            },
            row_count=len(items),
            allowed_user_ids=list(schedule.recipient_user_ids or []),
            created_by_user_id=schedule.created_by_user_id,
        )
        notified = _notify_recipients(
            session,
            organisation_id=schedule.organisation_id,
            recipients=list(schedule.recipient_user_ids or []),
            schedule_name=schedule.name,
            export_id=export.id,
            run_id=run.id,
        )
        run.status = "succeeded"
        run.finished_at = _now()
        run.report_export_id = export.id
        run.period_from = period_from
        run.period_to = period_to
        schedule.last_run_at = _now()
        schedule.next_run_at = schedule_service.next_run_after(schedule.frequency, _now())
        session.flush()
        return {
            "ok": True,
            "run_id": str(run.id),
            "export_id": str(export.id),
            "notified": notified,
            "rows": len(items),
        }
    except Exception as exc:  # noqa: BLE001 — record failure for retry
        logger.exception("Scheduled report failed schedule_id=%s", schedule_id)
        run.status = "failed"
        run.finished_at = _now()
        run.error_message = str(exc)[:2000]
        # Keep next_run_at near-term so beat can retry safely.
        schedule.next_run_at = _now() + timedelta(minutes=15)
        session.flush()
        return {"ok": False, "run_id": str(run.id), "error": str(exc)[:500]}


def dispatch_due_scheduled_reports(session: Session) -> dict[str, Any]:
    now = _now()
    due = session.scalars(
        select(ScheduledReport).where(
            ScheduledReport.is_enabled.is_(True),
            ScheduledReport.next_run_at.is_not(None),
            ScheduledReport.next_run_at <= now,
        )
    ).all()
    results = []
    for schedule in due:
        results.append(execute_scheduled_report(session, schedule.id))
    return {"processed": len(results), "results": results}


def dispatch_early_warning_scan(session: Session) -> dict[str, Any]:
    org_ids = list(session.scalars(select(Organisation.id)).all())
    results = []
    for oid in org_ids:
        results.append(alert_service.evaluate_organisation_alerts(session, oid))
    return {"organisations": len(results), "results": results}


def retry_failed_run(session: Session, run_id: uuid.UUID) -> dict[str, Any]:
    run = session.get(ScheduledReportRun, run_id)
    if run is None:
        return {"ok": False, "error": "run_not_found"}
    if run.status != "failed":
        return {"ok": False, "error": "not_failed"}
    if run.attempt_count >= 5:
        return {"ok": False, "error": "max_retries"}
    return execute_scheduled_report(session, run.scheduled_report_id, retry_run_id=run.id)
