"""RBAC helpers for F3.4 Notes Analysis."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access
from app.tenancy.context import OrganisationContext


def require_notes_analysis_run(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_NOTES_ANALYSIS_RUN)


def require_notes_analysis_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_NOTES_ANALYSIS_READ)


def require_notes_analysis_review(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_NOTES_ANALYSIS_REVIEW)


def require_notes_analysis_inbox(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_NOTES_ANALYSIS_INBOX_READ)


def assert_note_tenant_access(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID) -> None:
    assert_tenant_support_access(session, ctx, tenant_id)
