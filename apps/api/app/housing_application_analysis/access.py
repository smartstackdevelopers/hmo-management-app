"""RBAC for F3.8. Application visibility reuses the housing access gate."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.housing import HousingApplication
from app.housing import access as housing_access
from app.housing.service import get_application
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_run(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_HOUSING_APPLICATION_RUN)


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_HOUSING_APPLICATION_READ)


def require_review(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_HOUSING_APPLICATION_REVIEW)


def load_application(session: Session, ctx: OrganisationContext, application_id: uuid.UUID) -> HousingApplication:
    housing_access.require_application_read(ctx)
    return get_application(session, ctx, application_id)
