"""Deterministic metrics for report drafts — reuse F2.14 reporting summaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.reporting import caseload_reports, complaints_reports, housing_reports
from app.reporting.filters import CaseloadReportFilters, ComplaintsReportFilters, HousingReportFilters
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def collect_metrics(
    session: Session,
    ctx: OrganisationContext,
    *,
    period_start: datetime,
    period_end: datetime,
) -> dict[str, Any]:
    authz = ctx.authorization
    payload: dict[str, Any] = {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "sections": {},
        "unavailable": [],
        "metric_source": "f2.14_reporting_summaries",
    }
    housing_flt = HousingReportFilters(created_from=period_start, created_to=period_end, date_field="created_at")
    complaints_flt = ComplaintsReportFilters(created_from=period_start, created_to=period_end, date_field="created_at")
    caseload_flt = CaseloadReportFilters(created_from=period_start, created_to=period_end, date_field="created_at")

    if authz.has_permission(Permission.REPORTS_HOUSING_VIEW):
        payload["sections"]["housing"] = housing_reports.housing_summary(session, ctx, housing_flt)
    else:
        payload["unavailable"].append("housing")

    if authz.has_permission(Permission.REPORTS_COMPLAINTS_VIEW):
        payload["sections"]["complaints"] = complaints_reports.complaints_summary(session, ctx, complaints_flt)
    else:
        payload["unavailable"].append("complaints")

    if authz.has_permission(Permission.REPORTS_CASELOAD_VIEW):
        payload["sections"]["caseload"] = caseload_reports.caseload_summary(session, ctx, caseload_flt)
    else:
        payload["unavailable"].append("caseload")

    return payload
