"""RBAC for F3.6. Document visibility reuses the managed-document gate."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole
from app.db.models.managed_documents import ManagedDocument
from app.managed_documents.access import assert_document_readable, require_content
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_run(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_DOCUMENT_CHECK_RUN)
    require_content(ctx)


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_DOCUMENT_CHECK_READ)


def require_review(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.AI_DOCUMENT_CHECK_REVIEW)


def require_rules(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    if ctx.role != HMoreRole.ORGANISATION_ADMIN:
        require_permission(ctx.authorization, Permission.AI_DOCUMENT_CHECK_REVIEW)
    require_permission(ctx.authorization, Permission.AI_DOCUMENT_CHECK_REVIEW)


def load_document(session: Session, ctx: OrganisationContext, document_id: uuid.UUID) -> ManagedDocument:
    return assert_document_readable(session, ctx, document_id)
