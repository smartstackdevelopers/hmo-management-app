"""Authorisation for F2.5 housing applications."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.housing import HousingApplication
from app.db.models.membership import OrganisationMembership
from app.db.models.property import Property
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access
from app.tenancy.context import OrganisationContext


def require_application_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.APPLICATIONS_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_application_review(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.APPLICATIONS_REVIEW)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_application_create(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.APPLICATIONS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.APPLICATIONS_CREATE_ASSIGNED)
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.APPLICATIONS_CREATE_OWN)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_application_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.APPLICATIONS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.APPLICATIONS_READ_ASSIGNED)
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.APPLICATIONS_READ_OWN)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_waiting_list_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.WAITING_LIST_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_waiting_list_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.WAITING_LIST_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.WAITING_LIST_READ)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_active_org_member(
    session: Session, *, organisation_id: uuid.UUID, user_id: uuid.UUID
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


def get_tenant_or_404(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> Tenant:
    tenant = session.get(Tenant, tenant_id)
    if tenant is None or tenant.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


def assert_can_create_for_tenant(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID
) -> Tenant:
    tenant = get_tenant_or_404(session, ctx, tenant_id)
    if ctx.role == HMoreRole.TENANT:
        if tenant.user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return tenant
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        assert_tenant_support_access(session, ctx, tenant_id)
        return tenant
    return tenant


def assert_can_view_application(
    session: Session, ctx: OrganisationContext, application: HousingApplication
) -> None:
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        assert_tenant_support_access(session, ctx, application.tenant_id)
        return
    if ctx.role == HMoreRole.TENANT:
        tenant = get_tenant_or_404(session, ctx, application.tenant_id)
        if tenant.user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def assert_property_in_org(
    session: Session, ctx: OrganisationContext, property_id: uuid.UUID | None
) -> None:
    if property_id is None:
        return
    prop = session.get(Property, property_id)
    if prop is None or prop.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
