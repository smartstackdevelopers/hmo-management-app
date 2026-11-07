"""RBAC for F3.7. Case access reuses the support caseload gate."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.support.access import assert_tenant_support_access
from app.support_plans import access as sp_access
from app.tenancy.context import OrganisationContext


def require_run(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_SUPPORT_PLAN_DRAFT_RUN)


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_SUPPORT_PLAN_DRAFT_READ)


def require_review(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_SUPPORT_PLAN_DRAFT_REVIEW)


def assert_case_access(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID):
    return assert_tenant_support_access(session, ctx, tenant_id)


def assert_can_apply(session: Session, ctx: OrganisationContext, tenant_id: uuid.UUID):
    return sp_access.assert_tenant_scope_for_manage(session, ctx, tenant_id)
