"""Tenant self profile and assigned housing. No addresses are invented."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.tenant import Tenant
from app.records.audit_hook import record_crud_event
from app.records.tenant_service import find_own_tenant
from app.tenant_portal.schemas import TenantHousingOut, TenantSelfOut, TenantSelfUpdate
from app.tenancy.context import OrganisationContext

_SELF_FIELDS = frozenset({"preferred_name", "phone"})


def require_own_tenant(session: Session, ctx: OrganisationContext) -> Tenant:
    if ctx.role != HMoreRole.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant role required")
    tenant = find_own_tenant(session, ctx)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No linked tenant profile")
    return tenant


def get_own_profile(session: Session, ctx: OrganisationContext) -> TenantSelfOut:
    tenant = require_own_tenant(session, ctx)
    return TenantSelfOut.model_validate(tenant)


def update_own_profile(
    session: Session, ctx: OrganisationContext, data: TenantSelfUpdate
) -> TenantSelfOut:
    tenant = require_own_tenant(session, ctx)
    payload = data.model_dump(exclude_unset=True)
    rejected = set(payload) - _SELF_FIELDS
    if rejected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only preferred_name and phone can be updated",
        )
    if "preferred_name" in payload:
        tenant.preferred_name = payload["preferred_name"].strip()
    if "phone" in payload:
        phone = payload["phone"]
        tenant.phone = phone.strip() if isinstance(phone, str) and phone.strip() else None
    session.add(tenant)
    session.flush()
    session.refresh(tenant)
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        action="tenant.self_update",
        resource_type="tenant",
        resource_id=tenant.id,
        summary=f"Tenant updated own profile {tenant.preferred_name}",
    )
    return TenantSelfOut.model_validate(tenant)


def _property_view(session: Session, ctx: OrganisationContext, tenant: Tenant) -> dict | None:
    if tenant.assigned_property_id is None:
        return None
    row = session.get(Property, tenant.assigned_property_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        return None
    return {
        "id": row.id,
        "name": row.name,
        "address_line1": row.address_line1,
        "address_line2": row.address_line2,
        "city": row.city,
        "postcode": row.postcode,
    }


def _room_view(session: Session, ctx: OrganisationContext, tenant: Tenant) -> dict | None:
    if tenant.assigned_room_id is None:
        return None
    row = session.get(Room, tenant.assigned_room_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        return None
    return {"id": row.id, "label": row.label, "floor_label": row.floor_label}


def get_own_housing(session: Session, ctx: OrganisationContext) -> TenantHousingOut:
    """Return the caller's assignment only. The route does not accept another tenant id."""
    tenant = require_own_tenant(session, ctx)
    return TenantHousingOut.model_validate(
        {
            "tenancy_reference": tenant.tenancy_reference,
            "status": tenant.status,
            "property": _property_view(session, ctx, tenant),
            "room": _room_view(session, ctx, tenant),
        }
    )
