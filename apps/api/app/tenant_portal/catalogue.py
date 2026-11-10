"""Published community services and job/training listings for one organisation."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.catalogue import CommunityService, OpportunityListing
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.tenant_portal.schemas import (
    COMMUNITY_CATEGORIES,
    OPPORTUNITY_KINDS,
    CommunityServiceOut,
    CommunityServiceUpdate,
    CommunityServiceWrite,
    OpportunityOut,
    OpportunityUpdate,
    OpportunityWrite,
)
from app.tenancy.context import OrganisationContext


def require_catalogue_writer(ctx: OrganisationContext) -> None:
    """Organisation admin or super admin. Tenants cannot write catalogues."""
    if ctx.role in {HMoreRole.SUPER_ADMIN, HMoreRole.ORGANISATION_ADMIN}:
        return
    authz = ctx.authorization
    if authz.has_permission(Permission.ORGANISATIONS_MANAGE) or authz.has_permission(
        Permission.ORGANISATION_SETTINGS_MANAGE
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _require(ctx: OrganisationContext, permission: Permission) -> None:
    if not ctx.authorization.has_permission(permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {permission.value}",
        )


def _clean_query(q: str | None) -> str | None:
    if q is None:
        return None
    text = q.strip()
    return text or None


def list_community_services(
    session: Session,
    ctx: OrganisationContext,
    *,
    q: str | None,
    category: str | None,
) -> list[CommunityServiceOut]:
    _require(ctx, Permission.SERVICES_DISCOVER)
    if category is not None and category not in COMMUNITY_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category")
    stmt = select(CommunityService).where(
        CommunityService.organisation_id == ctx.organisation_id,
        CommunityService.is_published.is_(True),
    )
    if category:
        stmt = stmt.where(CommunityService.category == category)
    text = _clean_query(q)
    if text:
        pattern = f"%{text}%"
        stmt = stmt.where(
            or_(
                CommunityService.name.ilike(pattern),
                CommunityService.description.ilike(pattern),
                CommunityService.address_line.ilike(pattern),
            )
        )
    rows = list(session.scalars(stmt.order_by(CommunityService.name.asc())))
    return [CommunityServiceOut.model_validate(row) for row in rows]


def create_community_service(
    session: Session, ctx: OrganisationContext, data: CommunityServiceWrite
) -> CommunityServiceOut:
    require_catalogue_writer(ctx)
    if data.category not in COMMUNITY_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category")
    row = CommunityService(
        organisation_id=ctx.organisation_id,
        category=data.category,
        name=data.name.strip(),
        description=data.description,
        address_line=data.address_line,
        opening_hours=data.opening_hours,
        eligibility=data.eligibility,
        contact=data.contact,
        is_published=data.is_published,
    )
    session.add(row)
    session.flush()
    return CommunityServiceOut.model_validate(row)


def update_community_service(
    session: Session,
    ctx: OrganisationContext,
    service_id: uuid.UUID,
    data: CommunityServiceUpdate,
) -> CommunityServiceOut:
    require_catalogue_writer(ctx)
    row = session.get(CommunityService, service_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community service not found")
    payload = data.model_dump(exclude_unset=True)
    if "category" in payload and payload["category"] not in COMMUNITY_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category")
    if "name" in payload and payload["name"] is not None:
        payload["name"] = payload["name"].strip()
    for key, value in payload.items():
        setattr(row, key, value)
    session.add(row)
    session.flush()
    return CommunityServiceOut.model_validate(row)


def list_opportunities(
    session: Session,
    ctx: OrganisationContext,
    *,
    kind: str | None,
    q: str | None,
) -> list[OpportunityOut]:
    if kind is not None and kind not in OPPORTUNITY_KINDS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid kind")
    if kind == "training":
        _require(ctx, Permission.TRAINING_DISCOVER)
    else:
        _require(ctx, Permission.JOBS_DISCOVER)
    stmt = select(OpportunityListing).where(
        OpportunityListing.organisation_id == ctx.organisation_id,
        OpportunityListing.is_published.is_(True),
    )
    if kind:
        stmt = stmt.where(OpportunityListing.kind == kind)
    text = _clean_query(q)
    if text:
        pattern = f"%{text}%"
        stmt = stmt.where(
            or_(
                OpportunityListing.title.ilike(pattern),
                OpportunityListing.description.ilike(pattern),
                OpportunityListing.source_name.ilike(pattern),
            )
        )
    rows = list(session.scalars(stmt.order_by(OpportunityListing.title.asc())))
    return [OpportunityOut.model_validate(row) for row in rows]


def create_opportunity(
    session: Session, ctx: OrganisationContext, data: OpportunityWrite
) -> OpportunityOut:
    require_catalogue_writer(ctx)
    if data.kind not in OPPORTUNITY_KINDS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid kind")
    row = OpportunityListing(
        organisation_id=ctx.organisation_id,
        kind=data.kind,
        title=data.title.strip(),
        description=data.description,
        eligibility=data.eligibility,
        source_name=data.source_name,
        source_url=data.source_url,
        is_published=data.is_published,
    )
    session.add(row)
    session.flush()
    return OpportunityOut.model_validate(row)


def update_opportunity(
    session: Session,
    ctx: OrganisationContext,
    listing_id: uuid.UUID,
    data: OpportunityUpdate,
) -> OpportunityOut:
    require_catalogue_writer(ctx)
    row = session.get(OpportunityListing, listing_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    payload = data.model_dump(exclude_unset=True)
    if "kind" in payload and payload["kind"] not in OPPORTUNITY_KINDS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid kind")
    if "title" in payload and payload["title"] is not None:
        payload["title"] = payload["title"].strip()
    for key, value in payload.items():
        setattr(row, key, value)
    session.add(row)
    session.flush()
    return OpportunityOut.model_validate(row)
