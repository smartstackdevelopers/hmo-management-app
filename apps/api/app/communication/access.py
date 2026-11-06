"""Recipient-scope checks for F2.12 messaging (organisation + role + assignment)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.maintenance import MaintenanceRequest
from app.db.models.membership import OrganisationMembership
from app.db.models.property import Property
from app.db.models.support_ops import CaseAssignment
from app.db.models.tenant import Tenant
from app.tenancy.context import OrganisationContext


def _active_membership(session: Session, *, user_id: uuid.UUID, organisation_id: uuid.UUID) -> OrganisationMembership | None:
    return session.scalar(
        select(OrganisationMembership).where(
            OrganisationMembership.user_id == user_id,
            OrganisationMembership.organisation_id == organisation_id,
            OrganisationMembership.status == MembershipStatus.ACTIVE,
        )
    )


def assert_recipient_in_same_org(session: Session, organisation_id: uuid.UUID, recipient_user_id: uuid.UUID) -> None:
    if _active_membership(session, user_id=recipient_user_id, organisation_id=organisation_id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recipient is not in this organisation")


def assert_can_message(
    session: Session,
    ctx: OrganisationContext,
    *,
    recipient_user_id: uuid.UUID,
    conversation_tenant_id: uuid.UUID | None = None,
    conversation_property_id: uuid.UUID | None = None,
    conversation_maintenance_id: uuid.UUID | None = None,
) -> None:
    """Enforce who may message whom inside the active organisation."""
    assert_recipient_in_same_org(session, ctx.organisation_id, recipient_user_id)
    if ctx.user_id == recipient_user_id:
        return

    # Same-role staff messaging (e.g. org admin to admin) — allowed.
    recipient_membership = _active_membership(session, user_id=recipient_user_id, organisation_id=ctx.organisation_id)
    if recipient_membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recipient membership not found")

    if ctx.role == HMoreRole.SUPER_ADMIN:
        return

    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        return

    if ctx.role == HMoreRole.TENANT:
        # Tenants may message org admin / assigned support worker on their linked tenant row only.
        tenant = session.scalar(select(Tenant).where(Tenant.user_id == ctx.user_id, Tenant.organisation_id == ctx.organisation_id))
        if tenant is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant profile not linked")
        if recipient_membership.role == HMoreRole.ORGANISATION_ADMIN:
            return
        if recipient_membership.role == HMoreRole.SUPPORT_WORKER:
            assign = session.scalar(
                select(CaseAssignment).where(
                    CaseAssignment.organisation_id == ctx.organisation_id,
                    CaseAssignment.tenant_id == tenant.id,
                    CaseAssignment.support_worker_user_id == recipient_user_id,
                    CaseAssignment.status == "active",
                )
            )
            if assign is not None:
                return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant may not message this recipient")

    if ctx.role == HMoreRole.SUPPORT_WORKER:
        if recipient_membership.role == HMoreRole.ORGANISATION_ADMIN:
            return
        if recipient_membership.role == HMoreRole.TENANT:
            tenant = session.scalar(
                select(Tenant).where(
                    Tenant.user_id == recipient_user_id,
                    Tenant.organisation_id == ctx.organisation_id,
                )
            )
            if tenant is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recipient tenant profile missing")
            assign = session.scalar(
                select(CaseAssignment).where(
                    CaseAssignment.organisation_id == ctx.organisation_id,
                    CaseAssignment.tenant_id == tenant.id,
                    CaseAssignment.support_worker_user_id == ctx.user_id,
                    CaseAssignment.status == "active",
                )
            )
            if assign is not None:
                return
        if recipient_membership.role in {HMoreRole.SUPPORT_WORKER, HMoreRole.LANDLORD, HMoreRole.MAINTENANCE_CONTRACTOR}:
            # Scoped by optional conversation anchor when present.
            if conversation_tenant_id is not None:
                tenant = session.get(Tenant, conversation_tenant_id)
                if tenant and tenant.organisation_id == ctx.organisation_id:
                    assign = session.scalar(
                        select(CaseAssignment).where(
                            CaseAssignment.organisation_id == ctx.organisation_id,
                            CaseAssignment.tenant_id == tenant.id,
                            CaseAssignment.support_worker_user_id == ctx.user_id,
                            CaseAssignment.status == "active",
                        )
                    )
                    if assign is not None:
                        return
            if conversation_maintenance_id is not None:
                req = session.get(MaintenanceRequest, conversation_maintenance_id)
                if req and req.organisation_id == ctx.organisation_id:
                    # Contractor on the maintenance request, or another role tied to tenant.
                    if req.assigned_user_id == recipient_user_id or req.reported_by_user_id == recipient_user_id:
                        return
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Support worker cannot message this recipient")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Support worker messaging not permitted")

    if ctx.role == HMoreRole.LANDLORD:
        if recipient_membership.role != HMoreRole.TENANT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Landlord may only message tenants in-scope")
        tenant = session.scalar(
            select(Tenant).where(
                Tenant.user_id == recipient_user_id,
                Tenant.organisation_id == ctx.organisation_id,
            )
        )
        if tenant is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant not found")
        if conversation_property_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Landlord direct messages require a property-scoped conversation",
            )
        prop = session.get(Property, conversation_property_id)
        if prop is None or prop.organisation_id != ctx.organisation_id or prop.landlord_user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Property not authorised for this landlord")
        linked_maintenance = session.scalar(
            select(MaintenanceRequest.id).where(
                MaintenanceRequest.organisation_id == ctx.organisation_id,
                MaintenanceRequest.tenant_id == tenant.id,
                MaintenanceRequest.property_id == conversation_property_id,
            ).limit(1)
        )
        if linked_maintenance is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No authorised maintenance context links this tenant to the selected property",
            )
        return

    if ctx.role == HMoreRole.MAINTENANCE_CONTRACTOR:
        if recipient_membership.role == HMoreRole.ORGANISATION_ADMIN:
            return
        if conversation_maintenance_id is not None:
            req = session.get(MaintenanceRequest, conversation_maintenance_id)
            if req and req.organisation_id == ctx.organisation_id and req.assigned_user_id == ctx.user_id:
                if recipient_user_id in {req.reported_by_user_id, req.assigned_user_id}:
                    return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Contractor messaging not permitted")

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Messaging not permitted")
