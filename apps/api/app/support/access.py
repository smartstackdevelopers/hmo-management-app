"""Authorisation helpers for F2.1 caseload-scoped support records."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.membership import OrganisationMembership
from app.db.models.support_ops import CaseAssignment
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.rbac.service import assert_assigned_support_caseload, require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation


def require_caseload_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.SUPPORT_NOTES_READ_ASSIGNED)
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.TENANTS_READ)
        return
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_caseload_assign(ctx: OrganisationContext) -> None:
    """Org Admin (or Super Admin with org context) may manage assignments."""
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.TENANTS_MANAGE)
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only Organisation Admin may manage case assignments",
    )


def require_daily_log_write(ctx: OrganisationContext) -> None:
    """Support Workers author daily logs; Org Admin has read/oversight only."""
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.SUPPORT_NOTES_CREATE_ASSIGNED)
        return
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only Support Workers may author daily logs",
    )


def require_daily_log_oversight_edit(ctx: OrganisationContext) -> None:
    """Org Admin may void logs; authors may amend their own (checked in service)."""
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.TENANTS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.SUPPORT_NOTES_CREATE_ASSIGNED)
        return
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def get_tenant_or_404(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> Tenant:
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    assert_same_organisation(ctx.organisation_id, tenant.organisation_id)
    return tenant


def active_assignment_for_worker(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    tenant_id: uuid.UUID,
    worker_user_id: uuid.UUID,
) -> CaseAssignment | None:
    return session.scalar(
        select(CaseAssignment).where(
            CaseAssignment.organisation_id == organisation_id,
            CaseAssignment.tenant_id == tenant_id,
            CaseAssignment.support_worker_user_id == worker_user_id,
            CaseAssignment.status == "active",
        )
    )


def any_active_assignment(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> CaseAssignment | None:
    return session.scalar(
        select(CaseAssignment)
        .where(
            CaseAssignment.organisation_id == organisation_id,
            CaseAssignment.tenant_id == tenant_id,
            CaseAssignment.status == "active",
        )
        .limit(1)
    )


def assert_tenant_support_access(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
) -> Tenant:
    """Deny-by-default caseload gate for support-sensitive records."""
    require_caseload_read(ctx)
    tenant = get_tenant_or_404(session, ctx, tenant_id)

    if ctx.role == HMoreRole.SUPPORT_WORKER:
        assignment = active_assignment_for_worker(
            session,
            organisation_id=ctx.organisation_id,
            tenant_id=tenant.id,
            worker_user_id=ctx.user_id,
        )
        assert_assigned_support_caseload(
            ctx.authorization,
            organisation_id=tenant.organisation_id,
            assigned_support_worker_id=(
                assignment.support_worker_user_id if assignment else None
            ),
        )
        return tenant

    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        assert_assigned_support_caseload(
            ctx.authorization,
            organisation_id=tenant.organisation_id,
            assigned_support_worker_id=None,
        )
        return tenant

    if ctx.role == HMoreRole.SUPER_ADMIN:
        return tenant

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_worker_is_support_member(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    worker_user_id: uuid.UUID,
) -> None:
    membership = session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.user_id == worker_user_id,
            OrganisationMembership.role == HMoreRole.SUPPORT_WORKER,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be an active Support Worker in this organisation",
        )
