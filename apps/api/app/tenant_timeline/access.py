"""Authorisation for F2.9 tenant timeline, meetings, appointments, follow-ups, needs/goals."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.complaints import Complaint
from app.db.models.enums import HMoreRole
from app.db.models.maintenance import MaintenanceRequest
from app.db.models.property import Property
from app.db.models.tenant import Tenant
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access, get_tenant_or_404
from app.tenancy.context import OrganisationContext


def resolve_own_tenant_id(session: Session, ctx: OrganisationContext) -> uuid.UUID | None:
    row = session.scalar(
        select(Tenant.id).where(
            Tenant.organisation_id == ctx.organisation_id,
            Tenant.user_id == ctx.user_id,
        )
    )
    return row


def require_timeline_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.TIMELINE_READ)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.TIMELINE_READ)
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.TIMELINE_READ_OWN)
        return
    if ctx.role == HMoreRole.LANDLORD:
        require_permission(ctx.authorization, Permission.TIMELINE_READ_LANDLORD)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _landlord_has_property_scoped_activity(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> bool:
    """True when this landlord has a complaint or maintenance row linked to the tenant and their property."""
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


def assert_timeline_tenant_scope(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> Tenant:
    """Resolve tenant for timeline and sub-resources (meetings, appointments, etc.)."""
    require_timeline_read(ctx)
    tenant = get_tenant_or_404(session, ctx, tenant_id)

    if ctx.role == HMoreRole.SUPER_ADMIN:
        return tenant
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        return tenant
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        return assert_tenant_support_access(session, ctx, tenant_id)
    if ctx.role == HMoreRole.TENANT:
        if tenant.user_id != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        return tenant
    if ctx.role == HMoreRole.LANDLORD:
        if not _landlord_has_property_scoped_activity(session, ctx, tenant_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return tenant
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_landlord_timeline_activity_allowed(
    session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID
) -> None:
    """Deny landlords for activity types that are not property-scoped in this codebase."""
    if ctx.role != HMoreRole.LANDLORD:
        return
    if not _landlord_has_property_scoped_activity(session, ctx, tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_meeting_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER, HMoreRole.TENANT}:
        require_permission(ctx.authorization, Permission.TIMELINE_MEETING_READ)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_meeting_create(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}:
        require_permission(ctx.authorization, Permission.TIMELINE_MEETING_CREATE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def can_view_meeting_internal_notes(ctx: OrganisationContext) -> bool:
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return True
    if ctx.authorization and ctx.authorization.has_permission(Permission.TIMELINE_MEETING_NOTES_INTERNAL):
        return True
    return False


def require_appointment_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}:
        require_permission(ctx.authorization, Permission.TIMELINE_APPOINTMENT_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_followup_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}:
        require_permission(ctx.authorization, Permission.TIMELINE_FOLLOWUP_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_followup_read_assigned(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}:
        require_permission(ctx.authorization, Permission.TIMELINE_FOLLOWUP_READ_ASSIGNED)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_followup_list(ctx: OrganisationContext) -> None:
    """List/read follow-up summaries: staff use follow-up read; tenants use own timeline read."""
    if ctx.role == HMoreRole.TENANT:
        require_timeline_read(ctx)
        return
    require_followup_read_assigned(ctx)


def require_needs_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}:
        require_permission(ctx.authorization, Permission.TIMELINE_NEEDS_MANAGE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_needs_read(ctx: OrganisationContext) -> None:
    """Read structured needs/goals (tenant sees non-internal fields only in service)."""
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role in {HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPPORT_WORKER}:
        require_permission(ctx.authorization, Permission.TIMELINE_NEEDS_MANAGE)
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.TIMELINE_READ_OWN)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_followup_updater(ctx: OrganisationContext, assigned_user_id: uuid.UUID) -> None:
    """Follow-up updates: org admins may edit any; support workers only their assigned row."""
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER and assigned_user_id == ctx.user_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def assert_followup_reassign_allowed(ctx: OrganisationContext) -> None:
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only organisation admins may reassign")
