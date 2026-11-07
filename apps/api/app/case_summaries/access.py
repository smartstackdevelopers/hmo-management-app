"""RBAC for F3.5 case summaries. Case access reuses the F2.1 caseload gate."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access
from app.tenancy.context import OrganisationContext


def require_run(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_CASE_SUMMARY_RUN)


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_CASE_SUMMARY_READ)


def require_review(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_CASE_SUMMARY_REVIEW)


def assert_case_access(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID):
    return assert_tenant_support_access(session, ctx, tenant_id)
