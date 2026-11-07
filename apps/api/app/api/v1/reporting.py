"""F2.14 reporting and export API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.session import get_session
from app.reporting import (
    caseload_reports,
    complaints_reports,
    dashboard,
    exports,
    housing_reports,
)
from app.reporting.access import (
    require_export_csv,
    require_export_excel,
    require_export_pdf,
)
from app.reporting.filters import CaseloadReportFilters, ComplaintsReportFilters, HousingReportFilters
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/reports", tags=["reports"])

ReportType = Literal["housing", "complaints", "caseload"]
ExportFormat = Literal["csv", "pdf", "xlsx"]


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
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    flt = HousingReportFilters(
        created_from=created_from, created_to=created_to, date_field=date_field, status=status  # type: ignore[arg-type]
    )
    return housing_reports.housing_summary(session, org, flt)


@router.get("/housing/rows")
def housing_rows(
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    date_field: str = Query("created_at"),
    status: str | None = None,
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
    import uuid

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
    import uuid

    flt = CaseloadReportFilters(
        support_worker_user_id=uuid.UUID(support_worker_user_id) if support_worker_user_id else None,
        page=page,
        page_size=page_size,
    )
    items, total = caseload_reports.caseload_rows(session, org, flt)
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/export/{report_type}/{export_format}")
def export_report(
    report_type: ReportType,
    export_format: ExportFormat,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
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

    if report_type == "housing":
        flt = HousingReportFilters(created_from=created_from, created_to=created_to, page=1, page_size=page_size)
        summary = housing_reports.housing_summary(session, org, flt)
        items, _ = housing_reports.housing_rows(session, org, flt)
        headers = list(items[0].keys()) if items else ["reference_number", "status", "priority", "submitted_at"]
        title = "Housing applications report"
    elif report_type == "complaints":
        flt = ComplaintsReportFilters(created_from=created_from, created_to=created_to, page=1, page_size=page_size)
        summary = complaints_reports.complaints_summary(session, org, flt)
        items, _ = complaints_reports.complaints_rows(session, org, flt)
        headers = list(items[0].keys()) if items else ["reference_number", "status", "priority"]
        title = "Complaints report (operational deadlines)"
    else:
        flt = CaseloadReportFilters(page=1, page_size=page_size)
        summary = caseload_reports.caseload_summary(session, org, flt)
        items, _ = caseload_reports.caseload_rows(session, org, flt)
        headers = list(items[0].keys()) if items else ["tenant_id", "support_worker_user_id"]
        title = "Caseload report"

    _audit_export(
        session,
        org,
        report_type,
        export_format,
        {"from": created_from.isoformat() if created_from else None, "rows": len(items)},
    )
    from datetime import timezone

    filename = f"hmore-{report_type}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

    if export_format == "csv":
        body = exports.rows_to_csv(headers, items)
        return Response(
            content=body,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )
    if export_format == "pdf":
        lines = [f"{h}: {it.get(h)}" for it in items[:40] for h in headers[:4]]
        body = exports.summary_to_pdf(title, summary, lines)
        return Response(
            content=body,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
        )
    body = exports.rows_to_xlsx(report_type[:31], headers, items)
    return Response(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}.xlsx"'},
    )
