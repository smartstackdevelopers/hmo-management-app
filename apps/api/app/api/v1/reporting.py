"""F2.14 / F6.2 reporting, exports, schedules, and early-warning alerts API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.session import get_session
from app.reporting import (
    alerts as alert_service,
    caseload_reports,
    complaints_reports,
    dashboard,
    exports,
    housing_reports,
    jobs as reporting_jobs,
    occupancy_reports,
    plan_completion_reports,
    schedules as schedule_service,
    secure_exports,
)
from app.reporting.access import (
    require_export_csv,
    require_export_excel,
    require_export_pdf,
    require_schedule_manage,
)
from app.reporting.filters import (
    CaseloadReportFilters,
    ComplaintsReportFilters,
    HousingReportFilters,
    OccupancyReportFilters,
    PlanReportFilters,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/reports", tags=["reports"])

ReportType = Literal["housing", "complaints", "caseload", "occupancy", "plans"]
ExportFormat = Literal["csv", "pdf", "xlsx"]


class ScheduleCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    report_category: Literal["occupancy", "housing", "complaints", "caseload", "plans", "dashboard"]
    frequency: Literal["daily", "weekly", "monthly"]
    export_format: ExportFormat = "csv"
    period_days: int = Field(default=7, ge=1, le=366)
    filters: dict[str, Any] = Field(default_factory=dict)
    recipient_user_ids: list[str] = Field(default_factory=list)
    is_enabled: bool = True


class ScheduleUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_enabled: bool | None = None
    recipient_user_ids: list[str] | None = None
    filters: dict[str, Any] | None = None
    period_days: int | None = Field(default=None, ge=1, le=366)


class ThresholdBody(BaseModel):
    alert_type: str
    threshold_value: int = Field(ge=0)
    is_enabled: bool = True


class AlertStatusBody(BaseModel):
    status: Literal["open", "acknowledged", "resolved", "dismissed"]


def _audit_export(session: Session, ctx: OrganisationContext, report: str, fmt: str, meta: dict) -> None:
    action = {
        "csv": audit_events.REPORTS_EXPORT_CSV,
        "pdf": audit_events.REPORTS_EXPORT_PDF,
        "xlsx": audit_events.REPORTS_EXPORT_EXCEL,
    }.get(fmt, audit_events.REPORTS_EXPORT_CSV)
    record_event(
        session,
        action=action,
        resource_type="report_export",
        resource_id=report,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Exported {report} as {fmt}",
        metadata=meta,
        raise_on_error=False,
    )


def _load_report_bundle(
    session: Session,
    org: OrganisationContext,
    report_type: ReportType,
    *,
    created_from: datetime | None,
    created_to: datetime | None,
    page_size: int,
    property_id: uuid.UUID | None = None,
    support_worker_user_id: uuid.UUID | None = None,
    status: str | None = None,
) -> tuple[dict, list[dict], list[str], str]:
    if report_type == "housing":
        flt = HousingReportFilters(
            created_from=created_from,
            created_to=created_to,
            page=1,
            page_size=page_size,
            property_id=property_id,
            status=status,
        )
        summary = housing_reports.housing_summary(session, org, flt)
        items, _ = housing_reports.housing_rows(session, org, flt)
        headers = list(items[0].keys()) if items else ["reference_number", "status", "priority", "submitted_at"]
        return summary, items, headers, "Housing applications report"
    if report_type == "complaints":
        flt = ComplaintsReportFilters(
            created_from=created_from, created_to=created_to, page=1, page_size=page_size, status=status
        )
        summary = complaints_reports.complaints_summary(session, org, flt)
        items, _ = complaints_reports.complaints_rows(session, org, flt)
        headers = list(items[0].keys()) if items else ["reference_number", "status", "priority"]
        return summary, items, headers, "Complaints report (operational deadlines)"
    if report_type == "caseload":
        flt = CaseloadReportFilters(
            page=1, page_size=page_size, support_worker_user_id=support_worker_user_id
        )
        summary = caseload_reports.caseload_summary(session, org, flt)
        items, _ = caseload_reports.caseload_rows(session, org, flt)
        headers = list(items[0].keys()) if items else ["tenant_id", "support_worker_user_id"]
        return summary, items, headers, "Caseload report"
    if report_type == "occupancy":
        flt = OccupancyReportFilters(page=1, page_size=page_size, property_id=property_id)
        summary = occupancy_reports.occupancy_summary(session, org, flt)
        items, _ = occupancy_reports.occupancy_rows(session, org, flt)
        headers = list(items[0].keys()) if items else ["property_name", "room_label", "status"]
        return summary, items, headers, "Occupancy report"
    flt = PlanReportFilters(
        created_from=created_from,
        created_to=created_to,
        page=1,
        page_size=page_size,
        status=status,
        support_worker_user_id=support_worker_user_id,
    )
    summary = plan_completion_reports.plan_completion_summary(session, org, flt)
    items, _ = plan_completion_reports.plan_completion_rows(session, org, flt)
    headers = list(items[0].keys()) if items else ["reference_number", "status"]
    return summary, items, headers, "Support plan completion report"


@router.get("/dashboard")
def get_dashboard(
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return dashboard.main_dashboard(session, org, created_from=created_from, created_to=created_to)


@router.get("/housing/summary")
def housing_summary(
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    date_field: str = Query("created_at"),
    status: str | None = None,
    property_id: uuid.UUID | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = HousingReportFilters(
        created_from=created_from,
        created_to=created_to,
        date_field=date_field,  # type: ignore[arg-type]
        status=status,
        property_id=property_id,
    )
    return housing_reports.housing_summary(session, org, flt)


@router.get("/housing/rows")
def housing_rows(
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    date_field: str = Query("created_at"),
    status: str | None = None,
    property_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = HousingReportFilters(
        created_from=created_from,
        created_to=created_to,
        date_field=date_field,  # type: ignore[arg-type]
        status=status,
        property_id=property_id,
        page=page,
        page_size=page_size,
    )
    items, total = housing_reports.housing_rows(session, org, flt)
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/complaints/summary")
def complaints_summary(
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    status: str | None = None,
    priority: str | None = None,
    overdue_only: bool = False,
    escalated_only: bool = False,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = ComplaintsReportFilters(
        created_from=created_from,
        created_to=created_to,
        status=status,
        priority=priority,
        overdue_only=overdue_only,
        escalated_only=escalated_only,
    )
    return complaints_reports.complaints_summary(session, org, flt)


@router.get("/complaints/rows")
def complaints_rows(
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    status: str | None = None,
    priority: str | None = None,
    overdue_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = ComplaintsReportFilters(
        created_from=created_from,
        created_to=created_to,
        status=status,
        priority=priority,
        overdue_only=overdue_only,
        page=page,
        page_size=page_size,
    )
    items, total = complaints_reports.complaints_rows(session, org, flt)
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/caseload/summary")
def caseload_summary(
    support_worker_user_id: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = CaseloadReportFilters(
        support_worker_user_id=uuid.UUID(support_worker_user_id) if support_worker_user_id else None
    )
    return caseload_reports.caseload_summary(session, org, flt)


@router.get("/caseload/rows")
def caseload_rows(
    support_worker_user_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = CaseloadReportFilters(
        support_worker_user_id=uuid.UUID(support_worker_user_id) if support_worker_user_id else None,
        page=page,
        page_size=page_size,
    )
    items, total = caseload_reports.caseload_rows(session, org, flt)
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/occupancy/summary")
def occupancy_summary(
    property_id: uuid.UUID | None = None,
    building: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = OccupancyReportFilters(property_id=property_id, building=building)
    return occupancy_reports.occupancy_summary(session, org, flt)


@router.get("/occupancy/rows")
def occupancy_rows(
    property_id: uuid.UUID | None = None,
    building: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = OccupancyReportFilters(
        property_id=property_id, building=building, page=page, page_size=page_size
    )
    items, total = occupancy_reports.occupancy_rows(session, org, flt)
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/plans/summary")
def plans_summary(
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    status: str | None = None,
    support_worker_user_id: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = PlanReportFilters(
        created_from=created_from,
        created_to=created_to,
        status=status,
        support_worker_user_id=uuid.UUID(support_worker_user_id) if support_worker_user_id else None,
    )
    return plan_completion_reports.plan_completion_summary(session, org, flt)


@router.get("/plans/rows")
def plans_rows(
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    status: str | None = None,
    support_worker_user_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = PlanReportFilters(
        created_from=created_from,
        created_to=created_to,
        status=status,
        support_worker_user_id=uuid.UUID(support_worker_user_id) if support_worker_user_id else None,
        page=page,
        page_size=page_size,
    )
    items, total = plan_completion_reports.plan_completion_rows(session, org, flt)
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/export/{report_type}/{export_format}")
def export_report(
    report_type: ReportType,
    export_format: ExportFormat,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    property_id: uuid.UUID | None = None,
    support_worker_user_id: uuid.UUID | None = None,
    status: str | None = None,
    store: bool = Query(False, description="Persist export for authorised download"),
    page_size: int = Query(500, ge=1, le=2000),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    if export_format == "csv":
        require_export_csv(org)
    elif export_format == "pdf":
        require_export_pdf(org)
    else:
        require_export_excel(org)

    summary, items, headers, title = _load_report_bundle(
        session,
        org,
        report_type,
        created_from=created_from,
        created_to=created_to,
        page_size=page_size,
        property_id=property_id,
        support_worker_user_id=support_worker_user_id,
        status=status,
    )
    _audit_export(
        session,
        org,
        report_type,
        export_format,
        {
            "from": created_from.isoformat() if created_from else None,
            "to": created_to.isoformat() if created_to else None,
            "rows": len(items),
            "stored": store,
        },
    )
    from datetime import timezone

    filename = f"hmore-{report_type}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

    if export_format == "csv":
        body = exports.rows_to_csv(headers, items)
        media = "text/csv; charset=utf-8"
        ext = "csv"
    elif export_format == "pdf":
        lines = [f"{h}: {it.get(h)}" for it in items[:40] for h in headers[:4]]
        body = exports.summary_to_pdf(title, summary, lines)
        media = "application/pdf"
        ext = "pdf"
    else:
        body = exports.rows_to_xlsx(report_type[:31], headers, items)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"

    if store:
        artifact = secure_exports.store_report_export(
            session,
            org,
            category=report_type,
            export_format=export_format,
            title=title,
            body=body,
            filters={
                "from": created_from.isoformat() if created_from else None,
                "to": created_to.isoformat() if created_to else None,
            },
            row_count=len(items),
        )
        return Response(
            content=exports.rows_to_csv(
                ["export_id", "download_path", "title", "rows"],
                [
                    {
                        "export_id": str(artifact.id),
                        "download_path": f"/api/v1/reports/exports/{artifact.id}/download",
                        "title": title,
                        "rows": len(items),
                    }
                ],
            ),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}-stored.csv"'},
        )

    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{ext}"'},
    )


@router.get("/exports/{export_id}/download")
def download_stored_export(
    export_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    export, meta, data = secure_exports.get_export_bytes(session, org, export_id)
    return Response(
        content=data,
        media_type=meta.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{meta.original_filename}"',
        },
    )


@router.get("/schedules")
def list_schedules(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": schedule_service.list_schedules(session, org)}


@router.post("/schedules")
def create_schedule(
    body: ScheduleCreateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return schedule_service.create_schedule(
        session,
        org,
        name=body.name,
        report_category=body.report_category,
        frequency=body.frequency,
        export_format=body.export_format,
        period_days=body.period_days,
        filters=body.filters,
        recipient_user_ids=body.recipient_user_ids,
        is_enabled=body.is_enabled,
    )


@router.patch("/schedules/{schedule_id}")
def update_schedule(
    schedule_id: uuid.UUID,
    body: ScheduleUpdateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return schedule_service.update_schedule(
        session,
        org,
        schedule_id,
        name=body.name,
        is_enabled=body.is_enabled,
        recipient_user_ids=body.recipient_user_ids,
        filters=body.filters,
        period_days=body.period_days,
    )


@router.get("/schedules/runs")
def list_schedule_runs(
    schedule_id: uuid.UUID | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": schedule_service.list_runs(session, org, schedule_id)}


@router.post("/schedules/runs/{run_id}/retry")
def retry_schedule_run(
    run_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    require_schedule_manage(org)
    result = reporting_jobs.retry_failed_run(session, run_id)
    if not result.get("ok"):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=result.get("error", "retry_failed"))
    return result


@router.get("/alerts")
def list_alerts(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return alert_service.list_alerts(session, org, status_filter=status, page=page, page_size=page_size)


@router.patch("/alerts/{alert_id}")
def patch_alert(
    alert_id: uuid.UUID,
    body: AlertStatusBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return alert_service.update_alert_status(session, org, alert_id, new_status=body.status)


@router.get("/alerts/thresholds")
def get_thresholds(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": alert_service.list_thresholds(session, org)}


@router.put("/alerts/thresholds")
def put_threshold(
    body: ThresholdBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return alert_service.upsert_threshold(
        session,
        org,
        alert_type=body.alert_type,
        threshold_value=body.threshold_value,
        is_enabled=body.is_enabled,
    )


@router.post("/alerts/evaluate")
def evaluate_alerts_now(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    require_schedule_manage(org)
    return alert_service.evaluate_organisation_alerts(session, org.organisation_id)
