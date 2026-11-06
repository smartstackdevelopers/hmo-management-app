"""Authorisation for F2.3 training and safeguarding reminders."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.membership import OrganisationMembership
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access
from app.tenancy.context import OrganisationContext


def require_training_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.TRAINING_RECORDS_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_training_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.TRAINING_RECORDS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.TRAINING_RECORDS_READ_OWN)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_safeguarding_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.SAFEGUARDING_REMINDERS_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_safeguarding_access(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.SAFEGUARDING_REMINDERS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.SAFEGUARDING_REMINDERS_MANAGE_ASSIGNED)
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
            detail="User is not an active member of this organisation",
        )


def assert_tenant_in_org(session: Session, *, organisation_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    tenant = session.get(Tenant, tenant_id)
    if tenant is None or tenant.organisation_id != organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")


def assert_safeguarding_assignee_scope(
    session: Session,
    ctx: OrganisationContext,
    *,
    assigned_user_id: uuid.UUID,
    tenant_id: uuid.UUID | None,
) -> None:
    assert_active_org_member(
        session, organisation_id=ctx.organisation_id, user_id=assigned_user_id
    )
    if ctx.role == HMoreRole.SUPPORT_WORKER and assigned_user_id != ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Support workers may only assign safeguarding reminders to themselves",
        )
    if tenant_id is not None:
        assert_tenant_in_org(session, organisation_id=ctx.organisation_id, tenant_id=tenant_id)
        if ctx.role == HMoreRole.SUPPORT_WORKER:
            assert_tenant_support_access(session, ctx, tenant_id)
