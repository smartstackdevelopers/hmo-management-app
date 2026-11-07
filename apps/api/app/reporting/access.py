"""RBAC for F2.14 reporting."""

from __future__ import annotations

from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_dashboard(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.REPORTS_DASHBOARD_VIEW)


def require_housing_reports(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.REPORTS_HOUSING_VIEW)


def require_complaints_reports(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.REPORTS_COMPLAINTS_VIEW)


def require_caseload_reports(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.REPORTS_CASELOAD_VIEW)


def require_export_csv(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.REPORTS_EXPORT_CSV)


def require_export_pdf(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.REPORTS_EXPORT_PDF)


def require_export_excel(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.REPORTS_EXPORT_EXCEL)
