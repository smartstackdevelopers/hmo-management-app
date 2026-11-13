"""F8.7 benefits navigator access."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.benefits_navigator import BenefitsStaffConsentGrant
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from uuid import UUID


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_READ)


def require_tenant_data_access(
    session: Session, ctx: OrganisationContext, tenant_user_id: UUID
) -> None:
    if ctx.user_id == tenant_user_id or ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.BENEFITS_NAVIGATOR_STAFF_ASSIST)
    assert_staff_consent(session, ctx, tenant_user_id)


def assert_staff_consent(session: Session, ctx: OrganisationContext, tenant_user_id: UUID) -> None:
    if ctx.user_id == tenant_user_id:
        return
    now = datetime.now(timezone.utc)
    grant = session.scalar(
        select(BenefitsStaffConsentGrant).where(
            BenefitsStaffConsentGrant.organisation_id == ctx.organisation_id,
            BenefitsStaffConsentGrant.tenant_user_id == tenant_user_id,
            BenefitsStaffConsentGrant.support_user_id == ctx.user_id,
            BenefitsStaffConsentGrant.revoked_at.is_(None),
        )
    )
    if grant is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Tenant consent required")
    if grant.expires_at and grant.expires_at < now:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Consent expired")
