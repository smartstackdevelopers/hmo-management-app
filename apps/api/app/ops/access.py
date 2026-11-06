"""Authorisation for F2.2 scheduling operations."""

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
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access, get_tenant_or_404
from app.tenancy.context import OrganisationContext


def require_rota_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.ORGANISATION_USERS_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_rota_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.ORGANISATION_USERS_READ)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.VISITS_MANAGE_ASSIGNED)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_visits_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.TENANTS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.VISITS_MANAGE_ASSIGNED)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_tasks_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.TENANTS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.TASKS_MANAGE_ASSIGNED)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_active_org_member(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    membership = session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.user_id == user_id,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be an active member of this organisation",
        )


def assert_visit_assignee_scope(
    session: Session,
    ctx: OrganisationContext,
    *,
    tenant_id: uuid.UUID,
    assignee_user_id: uuid.UUID,
) -> Tenant:
    """SW may only schedule for assigned tenants and themselves as assignee."""
    require_visits_manage(ctx)
    tenant = get_tenant_or_404(session, ctx, tenant_id)
    assert_active_org_member(
        session, organisation_id=ctx.organisation_id, user_id=assignee_user_id
    )
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        if assignee_user_id != ctx.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Support Workers may only assign visits to themselves",
            )
        assert_tenant_support_access(session, ctx, tenant_id)
    return tenant


def assert_task_assignee_scope(
    session: Session,
    ctx: OrganisationContext,
    *,
    assignee_user_id: uuid.UUID,
    tenant_id: uuid.UUID | None,
) -> None:
    require_tasks_manage(ctx)
    assert_active_org_member(
        session, organisation_id=ctx.organisation_id, user_id=assignee_user_id
    )
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        if assignee_user_id != ctx.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Support Workers may only assign tasks to themselves",
            )
        if tenant_id is not None:
            assert_tenant_support_access(session, ctx, tenant_id)


def worker_has_active_assignment(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    tenant_id: uuid.UUID,
    worker_user_id: uuid.UUID,
) -> bool:
    row = session.scalar(
        select(CaseAssignment.id).where(
            CaseAssignment.organisation_id == organisation_id,
            CaseAssignment.tenant_id == tenant_id,
            CaseAssignment.support_worker_user_id == worker_user_id,
            CaseAssignment.status == "active",
        )
    )
    return row is not None
