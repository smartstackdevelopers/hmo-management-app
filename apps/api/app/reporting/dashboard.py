"""Combined operational dashboard (F2.14)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.reporting import (
    alerts as alert_service,
    caseload_reports,
    complaints_reports,
    housing_reports,
    occupancy_reports,
    plan_completion_reports,
)
from app.rbac.permissions import Permission
from app.reporting.access import require_dashboard
from app.reporting.filters import (
    CaseloadReportFilters,
    ComplaintsReportFilters,
    HousingReportFilters,
    OccupancyReportFilters,
    PlanReportFilters,
)
from app.tenancy.context import OrganisationContext


def main_dashboard(session: Session, ctx: OrganisationContext, *, created_from=None, created_to=None) -> dict[str, Any]:
    require_dashboard(ctx)
    housing_flt = HousingReportFilters(created_from=created_from, created_to=created_to)
    complaints_flt = ComplaintsReportFilters(created_from=created_from, created_to=created_to)
    caseload_flt = CaseloadReportFilters(created_from=created_from, created_to=created_to)
    occupancy_flt = OccupancyReportFilters(created_from=created_from, created_to=created_to)
    plans_flt = PlanReportFilters(created_from=created_from, created_to=created_to)
    payload: dict[str, Any] = {"generated_at": datetime.now(timezone.utc).isoformat()}
    authz = ctx.authorization
    if authz.has_permission(Permission.REPORTS_HOUSING_VIEW):
        payload["housing"] = housing_reports.housing_summary(session, ctx, housing_flt)
    if authz.has_permission(Permission.REPORTS_COMPLAINTS_VIEW):
        payload["complaints"] = complaints_reports.complaints_summary(session, ctx, complaints_flt)
    if authz.has_permission(Permission.REPORTS_CASELOAD_VIEW):
        payload["caseload"] = caseload_reports.caseload_summary(session, ctx, caseload_flt)
    if authz.has_permission(Permission.REPORTS_OCCUPANCY_VIEW):
        payload["occupancy"] = occupancy_reports.occupancy_summary(session, ctx, occupancy_flt)
    if authz.has_permission(Permission.REPORTS_PLANS_VIEW):
        payload["plans"] = plan_completion_reports.plan_completion_summary(session, ctx, plans_flt)
    if authz.has_permission(Permission.REPORTS_ALERTS_VIEW):
        open_alerts = alert_service.list_alerts(session, ctx, status_filter="open", page=1, page_size=5)
        payload["alerts"] = {
            "open_total": open_alerts["total"],
            "recent": open_alerts["items"],
        }
    return payload
