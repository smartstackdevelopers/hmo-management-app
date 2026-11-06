"""Authorisation for F2.6 evidence checklists and packs."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.housing import HousingApplication
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_evidence_manage(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.EVIDENCE_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.EVIDENCE_MANAGE_ASSIGNED)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_evidence_review(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.EVIDENCE_REVIEW)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_evidence_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.EVIDENCE_MANAGE)
        return
    if ctx.role == HMoreRole.SUPPORT_WORKER:
        require_permission(ctx.authorization, Permission.EVIDENCE_READ_ASSIGNED)
        return
    if ctx.role == HMoreRole.TENANT:
        require_permission(ctx.authorization, Permission.EVIDENCE_READ_OWN)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def require_pack_generate(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role == HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.EVIDENCE_PACK_GENERATE)
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def get_application_for_evidence(
    session: Session, ctx: OrganisationContext, application_id: uuid.UUID
) -> HousingApplication:
    """Reuse housing visibility so evidence stays scoped to permitted applications."""
    require_evidence_read(ctx)
    # Housing get_application enforces org + role visibility for the parent application.
    from app.housing import service as housing_service

    return housing_service.get_application(session, ctx, application_id)
