"""F8.5 contractor marketplace access."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.db.models.contractor_marketplace import ContractorDirectoryProfile, MarketplaceJob
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_READ)


def require_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_MANAGE)


def require_workspace(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.CONTRACTOR_MARKETPLACE_WORKSPACE)


def assert_job_visible(ctx: OrganisationContext, job: MarketplaceJob, profile: ContractorDirectoryProfile | None) -> None:
    if job.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    if ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR:
        if profile is None or job.assigned_contractor_profile_id != profile.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not assigned to this job")
