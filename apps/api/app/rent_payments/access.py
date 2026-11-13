"""F8.3 rent payments access."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.landlord_enterprise import RentRecord
from app.db.models.tenant import Tenant
from app.landlord_enterprise import access as landlord_access
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.LANDLORD}:
        require_permission(ctx.authorization, Permission.RENT_PAYMENTS_READ)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.RENT_PAYMENTS_READ_LIMITED)
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.RENT_PAYMENTS_READ_OWN)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.RENT_PAYMENTS_MANAGE)


def require_record(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.LANDLORD:
        require_permission(ctx.authorization, Permission.RENT_PAYMENTS_RECORD)
        return
    require_permission(ctx.authorization, Permission.RENT_PAYMENTS_MANAGE)


def resolve_own_tenant(session: Session, ctx: OrganisationContext) -> uuid.UUID:
    tenant = session.scalar(
        select(Tenant).where(Tenant.organisation_id == ctx.organisation_id, Tenant.user_id == ctx.user_id)
    )
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant profile linked")
    return tenant.id


def assert_rent_record_visible(session: Session, ctx: OrganisationContext, record: RentRecord) -> None:
    if record.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rent record not found")
    if ctx.role == HMoreRole.TENANT:
        own = resolve_own_tenant(session, ctx)
        if record.tenant_id != own:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your rent record")
        return
    if ctx.role == HMoreRole.LANDLORD:
        landlord_access.get_accessible_property(session, ctx, record.property_id)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER and not ctx.authorization.has_permission(Permission.RENT_PAYMENTS_MANAGE):
        if record.tenant_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Limited access")
