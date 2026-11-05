from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models.enums import MembershipStatus
from app.db.session import get_session
from app.rbac.context import AuthorizationContext
from app.rbac.deps import get_authorization_context
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context, get_platform_context
from app.tenancy.membership_service import (
    create_organisation,
    list_memberships_for_organisation,
    set_membership_status,
)

router = APIRouter(prefix="/organisations", tags=["organisations"])


class CreateOrganisationBody(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)


class MembershipStatusBody(BaseModel):
    status: str = Field(min_length=1, max_length=32)


@router.get("/me/context")
def my_organisation_context(
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    return {
        "organisation_id": str(ctx.organisation_id),
        "role": ctx.role.value,
        "user_id": str(ctx.user_id),
        "platform_bypass": ctx.platform_bypass,
    }


@router.post("")
def create_org(
    body: CreateOrganisationBody,
    authz: AuthorizationContext = Depends(get_platform_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        org = create_organisation(session, actor=authz, name=body.name, slug=body.slug)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"id": str(org.id), "name": org.name, "slug": org.slug}


@router.get("/{organisation_id}/memberships")
def list_org_memberships(
    organisation_id: uuid.UUID,
    authz: AuthorizationContext = Depends(get_authorization_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows = list_memberships_for_organisation(
        session, actor=authz, organisation_id=organisation_id
    )
    return {
        "organisation_id": str(organisation_id),
        "memberships": [
            {
                "id": str(row.id),
                "user_id": str(row.user_id),
                "role": row.role.value,
                "status": row.status.value,
            }
            for row in rows
        ],
    }


@router.patch("/memberships/{membership_id}/status")
def patch_membership_status(
    membership_id: uuid.UUID,
    body: MembershipStatusBody,
    authz: AuthorizationContext = Depends(get_authorization_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        status_value = MembershipStatus(body.status)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown membership status"
        ) from exc
    try:
        membership = set_membership_status(
            session,
            actor=authz,
            membership_id=membership_id,
            status=status_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "id": str(membership.id),
        "status": membership.status.value,
        "organisation_id": (
            str(membership.organisation_id) if membership.organisation_id else None
        ),
    }
