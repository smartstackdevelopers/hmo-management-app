"""Authorisation for F2.7 complaints."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.complaints import Complaint
from app.db.models.enums import HMoreRole
from app.db.models.property import Property
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access
from app.tenancy.context import OrganisationContext


def require_complaints_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.COMPLAINTS_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_complaints_create(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.COMPLAINTS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.COMPLAINTS_CREATE_ASSIGNED)
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.COMPLAINTS_CREATE_OWN)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_complaints_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.COMPLAINTS_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.COMPLAINTS_READ_ASSIGNED)
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.COMPLAINTS_READ_OWN)
        return
    if ctx.role == HMoreRole.LANDLORD:
        require_permission(ctx.authorization, Permission.COMPLAINTS_READ_PROPERTY)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def can_view_internal_notes(ctx: OrganisationContext) -> bool:
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return True
    return bool(ctx.authorization and ctx.authorization.has_permission(Permission.COMPLAINTS_NOTES_INTERNAL))


def assert_can_view_complaint(
    session: Session, ctx: OrganisationContext, complaint: Complaint
) -> None:
    require_complaints_read(ctx)
    if complaint.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return
    if ctx.role == HMoreRole.TENANT:
        tenant = session.scalar(
            select(Tenant).where(
                Tenant.organisation_id == ctx.organisation_id,
                Tenant.user_id == ctx.user_id,
            )
        )
        if tenant is None or complaint.tenant_id != tenant.id:
            if complaint.submitted_by_user_id != ctx.user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        if complaint.assigned_user_id == ctx.user_id:
            return
        if complaint.tenant_id is not None:
            assert_tenant_support_access(session, ctx, complaint.tenant_id)
            return
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    if ctx.role == HMoreRole.LANDLORD:
        if complaint.property_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
        prop = session.get(Property, complaint.property_id)
        if prop is None or prop.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
        if prop.landlord_user_id is not None and prop.landlord_user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def resolve_own_tenant_id(session: Session, ctx: OrganisationContext) -> uuid.UUID | None:
    tenant = session.scalar(
        select(Tenant).where(
            Tenant.organisation_id == ctx.organisation_id,
            Tenant.user_id == ctx.user_id,
        )
    )
    return tenant.id if tenant else None
