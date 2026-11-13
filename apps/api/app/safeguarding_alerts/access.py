"""Authorisation for F8.2 safeguarding alerts."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.tenant import Tenant
from app.db.models.safeguarding_alerts import SafeguardingAlert
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.safeguarding_alerts.constants import LANDLORD_VISIBLE_CATEGORY_SLUGS
from app.support.access import assert_tenant_support_access
from app.tenancy.context import OrganisationContext


def require_addon_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_READ)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_READ)
        return
    if ctx.role == HMoreRole.LANDLORD:
        require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_READ_PROPERTY)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_addon_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_MANAGE)


def require_rules_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_RULES_MANAGE)


def require_review_assigned(ctx: OrganisationContext) -> None:
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_REVIEW_ASSIGNED)


def require_escalate(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_ESCALATE)
        return
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_ESCALATE)


def require_tenant_report(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.SAFEGUARDING_ALERTS_TENANT_REPORT)


def assert_alert_visible(
    session: Session,
    ctx: OrganisationContext,
    alert: SafeguardingAlert,
    *,
    category_slug: str | None = None,
) -> None:
    if alert.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if ctx.role == HMoreRole.LANDLORD:
        if category_slug is None or category_slug not in LANDLORD_VISIBLE_CATEGORY_SLUGS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Property safety view only")
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER and not ctx.authorization.has_permission(
        Permission.SAFEGUARDING_ALERTS_MANAGE
    ):
        if alert.assigned_user_id != ctx.user_id and alert.tenant_id is not None:
            assert_tenant_support_access(session, ctx, alert.tenant_id)
        elif alert.assigned_user_id not in (None, ctx.user_id) and alert.tenant_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this alert")


def resolve_tenant_for_user(session: Session, ctx: OrganisationContext) -> uuid.UUID:
    tenant = session.scalar(
        select(Tenant).where(Tenant.organisation_id == ctx.organisation_id, Tenant.user_id == ctx.user_id)
    )
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant profile linked")
    return tenant.id


def assert_tenant_scope(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> None:
    if ctx.role == HMoreRole.TENANT:
        own = resolve_tenant_for_user(session, ctx)
        if own != tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant scope violation")
