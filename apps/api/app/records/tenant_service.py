from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, RecordStatus
from app.db.models.tenant import Tenant
from app.records.audit_hook import record_crud_event
from app.records.pagination import offset_limit
from app.records.schemas import TenantCreate, TenantUpdate
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import require_tenant_for_org


def _assert_tenant_visibility(ctx: OrganisationContext, tenant: Tenant) -> None:
    if ctx.role == HMoreRole.TENANT:
        if tenant.user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def create_tenant(session: Session, ctx: OrganisationContext, data: TenantCreate) -> Tenant:
    tenant = Tenant(
        organisation_id=ctx.organisation_id,
        preferred_name=data.preferred_name.strip(),
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        tenancy_reference=data.tenancy_reference,
        consent_notes=data.consent_notes,
        consent_given_at=data.consent_given_at,
        preferences=data.preferences,
        needs_goals=data.needs_goals,
        notes=data.notes,
        user_id=data.user_id,
        status=RecordStatus.ACTIVE,
    )
    session.add(tenant)
    session.flush()
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        action="tenant.create",
        resource_type="tenant",
        resource_id=tenant.id,
        summary=f"Created tenant {tenant.preferred_name}",
    )
    return tenant


def get_tenant(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> Tenant:
    tenant = require_tenant_for_org(session, ctx, tenant_id)
    _assert_tenant_visibility(ctx, tenant)
    return tenant


def list_tenants(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    status_filter: RecordStatus | None = None,
) -> tuple[list[Tenant], int]:
    stmt = select(Tenant).where(Tenant.organisation_id == ctx.organisation_id)
    if ctx.role == HMoreRole.TENANT:
        stmt = stmt.where(Tenant.user_id == ctx.user_id)
    if status_filter is not None:
        stmt = stmt.where(Tenant.status == status_filter)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Tenant.preferred_name.ilike(pattern),
                Tenant.full_name.ilike(pattern),
                Tenant.email.ilike(pattern),
                Tenant.tenancy_reference.ilike(pattern),
            )
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(stmt.order_by(Tenant.created_at.desc()).offset(offset).limit(limit))
    )
    return rows, total


def update_tenant(
    session: Session,
    ctx: OrganisationContext,
    tenant_id: uuid.UUID,
    data: TenantUpdate,
) -> Tenant:
    tenant = require_tenant_for_org(session, ctx, tenant_id)
    if ctx.role == HMoreRole.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    payload = data.model_dump(exclude_unset=True)
    if "preferred_name" in payload and payload["preferred_name"] is not None:
        payload["preferred_name"] = payload["preferred_name"].strip()
    for key, value in payload.items():
        setattr(tenant, key, value)
    session.add(tenant)
    session.flush()
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        action="tenant.update",
        resource_type="tenant",
        resource_id=tenant.id,
        summary=f"Updated tenant {tenant.preferred_name}",
    )
    return tenant


def archive_tenant(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> Tenant:
    tenant = require_tenant_for_org(session, ctx, tenant_id)
    if ctx.role == HMoreRole.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tenant.status = RecordStatus.ARCHIVED
    session.add(tenant)
    session.flush()
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        action="tenant.archive",
        resource_type="tenant",
        resource_id=tenant.id,
        summary=f"Archived tenant {tenant.preferred_name}",
    )
    return tenant


def find_own_tenant(session: Session, ctx: OrganisationContext) -> Tenant | None:
    if ctx.role != HMoreRole.TENANT:
        return None
    return session.scalar(
        select(Tenant).where(
            Tenant.organisation_id == ctx.organisation_id,
            Tenant.user_id == ctx.user_id,
        )
    )
