"""RBAC helpers for F2.13."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.rbac.context import AuthorizationContext
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_inbox_read(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.APPROVALS_INBOX_READ)


def require_approval_decide(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.APPROVALS_DECIDE)


def require_approval_assign(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.APPROVALS_ASSIGN)


def require_workflow_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.ORGANISATION_WORKFLOWS_MANAGE)


def require_forms_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.ORGANISATION_FORMS_MANAGE)


def require_forms_publish(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.ORGANISATION_FORMS_PUBLISH)


def require_forms_submit(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.ORGANISATION_FORMS_SUBMIT)


def require_submissions_read(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.ORGANISATION_FORMS_SUBMISSIONS_READ)


def require_submissions_review(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.ORGANISATION_FORMS_SUBMISSIONS_REVIEW)


def require_sharing_grant(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.SECURE_SHARING_GRANT)


def require_sharing_revoke(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.SECURE_SHARING_REVOKE)


def require_sharing_read(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.SECURE_SHARING_READ)


def deny_unless(authz: AuthorizationContext, permission: Permission) -> None:
    if not authz.has_permission(permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
