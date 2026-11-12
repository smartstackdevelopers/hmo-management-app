"""RBAC for Council Portal manage (core roles) vs officer access (add-on table)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.council_portal.constants import ADDON_ROLE_LABEL
from app.council_portal.context import CouncilPortalContext
from app.db.models.council_portal import CouncilPortalOfficer
from app.db.models.user import User
from app.db.session import get_session
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls


def require_council_portal_manage(ctx: OrganisationContext) -> None:
    require_permission(ctx.authorization, Permission.COUNCIL_PORTAL_MANAGE)


def get_council_officer_context(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    x_organisation_id: Annotated[str | None, Header(alias="X-Organisation-Id")] = None,
) -> CouncilPortalContext:
    """Resolve council officer without requiring a core HMoreRole membership for this org.

    Officers must still be authenticated users. Organisation boundary comes from header +
    active CouncilPortalOfficer row — never from inventing a seventh HMoreRole.
    """
    if not x_organisation_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="X-Organisation-Id required for Council Portal officer access",
        )
    try:
        org_id = uuid.UUID(x_organisation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid X-Organisation-Id") from exc

    officer = session.scalar(
        select(CouncilPortalOfficer).where(
            CouncilPortalOfficer.organisation_id == org_id,
            CouncilPortalOfficer.user_id == user.id,
            CouncilPortalOfficer.status == "active",
            CouncilPortalOfficer.addon_role_label == ADDON_ROLE_LABEL,
        )
    )
    if officer is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not an active council portal officer for this organisation",
        )
    apply_organisation_rls(session, org_id)
    return CouncilPortalContext(
        user=user,
        organisation_id=org_id,
        officer_id=officer.id,
        addon_role_label=officer.addon_role_label,
    )
