"""Authorisation for F2.10 structured support plans."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.complaints import Complaint
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.maintenance import MaintenanceRequest
from app.db.models.membership import OrganisationMembership
from app.db.models.property import Property
from app.db.models.support_ops import CaseAssignment
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.rbac.service import assert_assigned_support_caseload, require_permission
from app.support.access import get_tenant_or_404, require_caseload_read
from app.tenancy.context import OrganisationContext


def resolve_own_tenant_id(session: Session, ctx: OrganisationContext) -> uuid.UUID | None:
    row = session.scalar(
        select(Tenant.id).where(
            Tenant.organisation_id == ctx.organisation_id,
            Tenant.user_id == ctx.user_id,
        )
    )
    return row


def _landlord_has_property_scoped_activity(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> bool:
    """Same scope rule as tenant timeline (property-linked complaint or maintenance)."""
    c = session.scalar(
        select(Complaint.id)
        .join(Property, Property.id == Complaint.property_id)
        .where(
            Complaint.organisation_id == ctx.organisation_id,
            Complaint.tenant_id == tenant_id,
            Property.organisation_id == ctx.organisation_id,
            Property.landlord_user_id == ctx.user_id,
        )
        .limit(1)
    )
    if c is not None:
        return True
    m = session.scalar(
        select(MaintenanceRequest.id)
        .join(Property, Property.id == MaintenanceRequest.property_id)
        .where(
            MaintenanceRequest.organisation_id == ctx.organisation_id,
            MaintenanceRequest.tenant_id == tenant_id,
            Property.organisation_id == ctx.organisation_id,
            Property.landlord_user_id == ctx.user_id,
        )
        .limit(1)
    )
    return m is not None


def require_support_plan_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.SUPPORT_PLAN_READ)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.SUPPORT_PLAN_READ)
        return
    if ctx.role == HMoreRole.LANDLORD:
        require_permission(ctx.authorization, Permission.SUPPORT_PLAN_READ)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_support_plan_read_tenant(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.SUPPORT_PLAN_READ_OWN)
        return
    require_support_plan_read(ctx)


def require_support_plan_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.SUPPORT_PLAN_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.SUPPORT_PLAN_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def can_view_internal_notes(ctx: OrganisationContext) -> bool:
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return True
    if ctx.authorization and ctx.authorization.has_permission(Permission.SUPPORT_PLAN_NOTES_INTERNAL):
        return True
    return False


def require_review_finalise(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}:
        require_permission(ctx.authorization, Permission.SUPPORT_PLAN_REVIEW_FINALISE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_export(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}:
        require_permission(ctx.authorization, Permission.SUPPORT_PLAN_EXPORT)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_tenant_scope(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> Tenant:
    """Resolve tenant for support-plan routes (caseload, org admin, tenant own, scoped landlord)."""
    if ctx.role == HMoreRole.TENANT:
        require_support_plan_read_tenant(ctx)
    else:
        require_support_plan_read(ctx)
    tenant = get_tenant_or_404(session, ctx, tenant_id)

    if ctx.role == HMoreRole.SUPER_ADMIN:
        return tenant
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        return tenant
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_caseload_read(ctx)
        assignment = session.scalar(
            select(CaseAssignment).where(
                CaseAssignment.organisation_id == ctx.organisation_id,
                CaseAssignment.tenant_id == tenant_id,
                CaseAssignment.support_worker_user_id == ctx.user_id,
                CaseAssignment.status == "active",
            )
        )
        assert_assigned_support_caseload(
            ctx.authorization,
            organisation_id=tenant.organisation_id,
            assigned_support_worker_id=(assignment.support_worker_user_id if assignment else None),
        )
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return tenant
    if ctx.role == HMoreRole.TENANT:
        if tenant.user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        return tenant
    if ctx.role == HMoreRole.LANDLORD:
        if not _landlord_has_property_scoped_activity(session, ctx, tenant_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return tenant
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_tenant_scope_for_manage(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> Tenant:
    """Manage operations: Support Worker caseload, Org Admin, Super Admin only."""
    require_support_plan_manage(ctx)
    tenant = get_tenant_or_404(session, ctx, tenant_id)
    if ctx.role == HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.SUPPORT_PLAN_MANAGE)
        return tenant
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        return tenant
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_caseload_read(ctx)
        assignment = session.scalar(
            select(CaseAssignment).where(
                CaseAssignment.organisation_id == ctx.organisation_id,
                CaseAssignment.tenant_id == tenant_id,
                CaseAssignment.support_worker_user_id == ctx.user_id,
                CaseAssignment.status == "active",
            )
        )
        assert_assigned_support_caseload(
            ctx.authorization,
            organisation_id=tenant.organisation_id,
            assigned_support_worker_id=(assignment.support_worker_user_id if assignment else None),
        )
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return tenant
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_worker_membership(session: Session, organisation_id: uuid.UUID, user_id: uuid.UUID) -> None:
    m = session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.user_id == user_id,
            OrganisationMembership.role == HMoreRole.SUPPORT_WORKER,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Responsible worker must be a Support Worker in this organisation",
        )


def is_plan_contributor(
    session: Session,
    *,
    plan_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    from app.db.models.support_plans import SupportPlanContributor

    row = session.scalar(
        select(SupportPlanContributor.id).where(
            SupportPlanContributor.plan_id == plan_id,
            SupportPlanContributor.user_id == user_id,
        )
    )
    return row is not None
