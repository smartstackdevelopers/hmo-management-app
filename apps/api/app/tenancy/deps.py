"""FastAPI dependencies for organisation isolation (built on F1.3 + F1.4)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.tokens import http_403
from app.db.models.enums import HMoreRole
from app.db.session import get_session
from app.rbac.context import AuthorizationContext
from app.rbac.deps import get_authorization_context
from app.tenancy.context import OrganisationContext, from_authorization
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def get_organisation_context(
    authz: AuthorizationContext = Depends(get_authorization_context),
    session: Session = Depends(get_session),
) -> OrganisationContext:
    """Require a trusted organisation boundary for tenant-scoped operations.

    Super Admin must send a validated X-Organisation-Id to enter an org scope.
    Ordinary tenant-scoped endpoints never grant unrestricted cross-org access.
    """
    ctx = from_authorization(authz, require_organisation=True)
    if ctx is None:
        if authz.active_role == HMoreRole.SUPER_ADMIN:
            raise http_403(
                "Organisation context required; send X-Organisation-Id for "
                "organisation-scoped operations"
            )
        raise http_403("Organisation context required")

    apply_organisation_rls(session, ctx.organisation_id)
    return ctx


def get_platform_context(
    authz: AuthorizationContext = Depends(get_authorization_context),
    session: Session = Depends(get_session),
) -> AuthorizationContext:
    """Explicit platform-level context (Super Admin only). Enables RLS bypass."""
    if authz.active_role != HMoreRole.SUPER_ADMIN:
        raise http_403("Platform operation requires Super Admin")
    apply_platform_rls_bypass(session)
    return authz
