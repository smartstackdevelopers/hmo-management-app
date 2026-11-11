"""Published community services and job/training listings for one organisation.

F5.1 extends community services with verification, pagination, detail retrieval,
and administrative management. Tenants never receive verification notes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.catalogue import (
    CLOTHING_SERVICE_TYPES,
    VERIFICATION_STATUSES,
    CommunityService,
    CommunityServiceVerificationEvent,
    OpportunityListing,
)
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.tenant_portal.schemas import (
    COMMUNITY_CATEGORIES,
    DIRECTORY_PRIMARY_CATEGORIES,
    OPPORTUNITY_KINDS,
    CommunityServiceAdminOut,
    CommunityServiceAdminPage,
    CommunityServiceDeactivateBody,
    CommunityServiceFlagBody,
    CommunityServiceOut,
    CommunityServicePage,
    CommunityServiceUpdate,
    CommunityServiceVerifyBody,
    CommunityServiceWrite,
    OpportunityOut,
    OpportunityUpdate,
    OpportunityWrite,
    VerificationEventOut,
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


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _validate_category(category: str) -> None:
    if category not in COMMUNITY_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category")


def _validate_clothing_type(category: str, clothing_service_type: str | None) -> None:
    if clothing_service_type is None:
        return
    if clothing_service_type not in CLOTHING_SERVICE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid clothing_service_type",
        )
    if category != "clothing_bank":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="clothing_service_type is only valid for clothing_bank",
        )


def _validate_opening_hours(opening_hours: str | None) -> None:
    """Reject obviously invalid hour strings; do not invent schedules."""
    if opening_hours is None:
        return
    text = opening_hours.strip()
    if not text:
        return
    if len(text) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="opening_hours too long",
        )


def _paginate(page: int, page_size: int) -> tuple[int, int]:
    safe_page = max(1, page)
    safe_size = min(max(1, page_size), 100)
    return safe_page, safe_size


def _tenant_out(row: CommunityService) -> CommunityServiceOut:
    return CommunityServiceOut.model_validate(row)


def _admin_out(row: CommunityService) -> CommunityServiceAdminOut:
    return CommunityServiceAdminOut.model_validate(row)


def _audit(
    session: Session,
    ctx: OrganisationContext,
    *,
    action: str,
    row: CommunityService,
    summary: str,
    metadata: dict | None = None,
) -> None:
    record_event(
        session,
        action=action,
        resource_type="community_service",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary=summary,
        metadata={
            "category": row.category,
            "verification_status": row.verification_status,
            "is_published": row.is_published,
            **(metadata or {}),
        },
    )


def _append_history(
    session: Session,
    ctx: OrganisationContext,
    row: CommunityService,
    *,
    action: str,
    from_status: str | None,
    to_status: str,
    notes: str | None,
) -> None:
    session.add(
        CommunityServiceVerificationEvent(
            organisation_id=ctx.organisation_id,
            service_id=row.id,
            from_status=from_status,
            to_status=to_status,
            action=action,
            notes=_optional_text(notes),
            actor_user_id=ctx.user_id,
        )
    )


def _find_duplicate(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    category: str,
    name: str,
    exclude_id: uuid.UUID | None = None,
) -> CommunityService | None:
    stmt = select(CommunityService).where(
        CommunityService.organisation_id == organisation_id,
        CommunityService.category == category,
        func.lower(CommunityService.name) == name.strip().lower(),
        CommunityService.verification_status != "inactive",
    )
    if exclude_id is not None:
        stmt = stmt.where(CommunityService.id != exclude_id)
    return session.scalar(stmt.limit(1))


def list_service_categories(ctx: OrganisationContext) -> dict[str, list[dict[str, str]]]:
    _require(ctx, Permission.SERVICES_DISCOVER)
    labels = {
        "food_bank": "Food banks",
        "kitchen": "Community kitchens",
        "clothing_bank": "Clothing banks",
        "local_service": "Local services",
    }
    return {
        "items": [
            {"id": category, "label": labels[category]}
            for category in (*DIRECTORY_PRIMARY_CATEGORIES, "local_service")
        ]
    }


def list_community_services(
    session: Session,
    ctx: OrganisationContext,
    *,
    q: str | None,
    category: str | None,
    page: int = 1,
    page_size: int = 50,
    has_opening_hours: bool | None = None,
    has_eligibility: bool | None = None,
) -> CommunityServicePage:
    """Tenant directory: published, non-inactive listings only."""
    _require(ctx, Permission.SERVICES_DISCOVER)
    if category is not None:
        _validate_category(category)
    page, page_size = _paginate(page, page_size)
    filters = [
        CommunityService.organisation_id == ctx.organisation_id,
        CommunityService.is_published.is_(True),
        CommunityService.verification_status != "inactive",
    ]
    if category:
        filters.append(CommunityService.category == category)
    text = _clean_query(q)
    if text:
        pattern = f"%{text}%"
        filters.append(
            or_(
                CommunityService.name.ilike(pattern),
                CommunityService.description.ilike(pattern),
                CommunityService.address_line.ilike(pattern),
            )
        )
    if has_opening_hours is True:
        filters.append(CommunityService.opening_hours.is_not(None))
        filters.append(CommunityService.opening_hours != "")
    elif has_opening_hours is False:
        filters.append(
            or_(CommunityService.opening_hours.is_(None), CommunityService.opening_hours == "")
        )
    if has_eligibility is True:
        filters.append(CommunityService.eligibility.is_not(None))
        filters.append(CommunityService.eligibility != "")
    elif has_eligibility is False:
        filters.append(
            or_(CommunityService.eligibility.is_(None), CommunityService.eligibility == "")
        )

    total = session.scalar(select(func.count()).select_from(CommunityService).where(*filters)) or 0
    rows = list(
        session.scalars(
            select(CommunityService)
            .where(*filters)
            .order_by(CommunityService.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return CommunityServicePage(
        items=[_tenant_out(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def list_admin_community_services(
    session: Session,
    ctx: OrganisationContext,
    *,
    q: str | None,
    category: str | None,
    verification_status: str | None,
    page: int = 1,
    page_size: int = 50,
) -> CommunityServiceAdminPage:
    require_catalogue_writer(ctx)
    if category is not None:
        _validate_category(category)
    if verification_status is not None and verification_status not in VERIFICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid verification_status",
        )
    page, page_size = _paginate(page, page_size)
    filters = [CommunityService.organisation_id == ctx.organisation_id]
    if category:
        filters.append(CommunityService.category == category)
    if verification_status:
        filters.append(CommunityService.verification_status == verification_status)
    text = _clean_query(q)
    if text:
        pattern = f"%{text}%"
        filters.append(
            or_(
                CommunityService.name.ilike(pattern),
                CommunityService.description.ilike(pattern),
                CommunityService.address_line.ilike(pattern),
            )
        )
    total = session.scalar(select(func.count()).select_from(CommunityService).where(*filters)) or 0
    rows = list(
        session.scalars(
            select(CommunityService)
            .where(*filters)
            .order_by(CommunityService.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return CommunityServiceAdminPage(
        items=[_admin_out(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def get_community_service(
    session: Session,
    ctx: OrganisationContext,
    service_id: uuid.UUID,
    *,
    admin: bool = False,
) -> CommunityServiceOut | CommunityServiceAdminOut:
    if admin:
        require_catalogue_writer(ctx)
    else:
        _require(ctx, Permission.SERVICES_DISCOVER)
    row = session.get(CommunityService, service_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community service not found")
    if not admin:
        if not row.is_published or row.verification_status == "inactive":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community service not found",
            )
        return _tenant_out(row)
    return _admin_out(row)


def create_community_service(
    session: Session, ctx: OrganisationContext, data: CommunityServiceWrite
) -> CommunityServiceAdminOut:
    require_catalogue_writer(ctx)
    _validate_category(data.category)
    _validate_clothing_type(data.category, data.clothing_service_type)
    _validate_opening_hours(data.opening_hours)
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="name is required")
    if _find_duplicate(
        session,
        organisation_id=ctx.organisation_id,
        category=data.category,
        name=name,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A service with this name and category already exists",
        )
    row = CommunityService(
        organisation_id=ctx.organisation_id,
        category=data.category,
        name=name,
        description=_optional_text(data.description),
        address_line=_optional_text(data.address_line),
        opening_days=_optional_text(data.opening_days),
        opening_hours=_optional_text(data.opening_hours),
        eligibility=_optional_text(data.eligibility),
        referral_requirements=_optional_text(data.referral_requirements),
        contact=_optional_text(data.contact),
        service_instructions=_optional_text(data.service_instructions),
        clothing_service_type=data.clothing_service_type,
        information_source=_optional_text(data.information_source),
        is_published=data.is_published,
        verification_status="pending_verification",
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
    )
    session.add(row)
    session.flush()
    _append_history(
        session,
        ctx,
        row,
        action="created",
        from_status=None,
        to_status="pending_verification",
        notes="Listing created; pending verification",
    )
    _audit(
        session,
        ctx,
        action=audit_events.COMMUNITY_SERVICE_CREATE,
        row=row,
        summary="Community service listing created",
    )
    session.flush()
    return _admin_out(row)


def update_community_service(
    session: Session,
    ctx: OrganisationContext,
    service_id: uuid.UUID,
    data: CommunityServiceUpdate,
) -> CommunityServiceAdminOut:
    require_catalogue_writer(ctx)
    row = session.get(CommunityService, service_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community service not found")
    payload = data.model_dump(exclude_unset=True)
    if "category" in payload and payload["category"] is not None:
        _validate_category(payload["category"])
    category = payload.get("category", row.category)
    clothing_type = payload.get("clothing_service_type", row.clothing_service_type)
    if "clothing_service_type" in payload or "category" in payload:
        _validate_clothing_type(category, clothing_type)
    if "opening_hours" in payload:
        _validate_opening_hours(payload.get("opening_hours"))
    if "name" in payload and payload["name"] is not None:
        payload["name"] = payload["name"].strip()
        if not payload["name"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="name is required",
            )
    check_name = payload.get("name", row.name)
    check_category = category
    if _find_duplicate(
        session,
        organisation_id=ctx.organisation_id,
        category=check_category,
        name=check_name,
        exclude_id=row.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A service with this name and category already exists",
        )
    text_fields = {
        "description",
        "address_line",
        "opening_days",
        "opening_hours",
        "eligibility",
        "referral_requirements",
        "contact",
        "service_instructions",
        "information_source",
    }
    for key, value in payload.items():
        if key in text_fields and isinstance(value, str):
            setattr(row, key, _optional_text(value))
        else:
            setattr(row, key, value)
    # Content edits move verified listings back to needs_review unless inactive.
    if row.verification_status == "verified" and any(
        key in payload
        for key in (
            "name",
            "description",
            "address_line",
            "opening_days",
            "opening_hours",
            "eligibility",
            "referral_requirements",
            "contact",
            "service_instructions",
            "clothing_service_type",
            "category",
        )
    ):
        previous = row.verification_status
        row.verification_status = "needs_review"
        _append_history(
            session,
            ctx,
            row,
            action="content_updated",
            from_status=previous,
            to_status="needs_review",
            notes="Content updated; re-verification required",
        )
    row.updated_by_user_id = ctx.user_id
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.COMMUNITY_SERVICE_UPDATE,
        row=row,
        summary="Community service listing updated",
        metadata={"fields": sorted(payload.keys())},
    )
    return _admin_out(row)


def verify_community_service(
    session: Session,
    ctx: OrganisationContext,
    service_id: uuid.UUID,
    data: CommunityServiceVerifyBody,
) -> CommunityServiceAdminOut:
    require_catalogue_writer(ctx)
    row = session.get(CommunityService, service_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community service not found")
    if row.verification_status == "inactive":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inactive listings cannot be verified; restore via edit first",
        )
    previous = row.verification_status
    row.verification_status = "verified"
    row.verified_at = datetime.now(timezone.utc)
    row.verified_by_user_id = ctx.user_id
    row.updated_by_user_id = ctx.user_id
    row.verification_notes = _optional_text(data.notes)
    if data.publish:
        row.is_published = True
    session.add(row)
    _append_history(
        session,
        ctx,
        row,
        action="verified",
        from_status=previous,
        to_status="verified",
        notes=data.notes,
    )
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.COMMUNITY_SERVICE_VERIFY,
        row=row,
        summary="Community service listing verified",
    )
    return _admin_out(row)


def flag_outdated_community_service(
    session: Session,
    ctx: OrganisationContext,
    service_id: uuid.UUID,
    data: CommunityServiceFlagBody,
) -> CommunityServiceAdminOut:
    require_catalogue_writer(ctx)
    row = session.get(CommunityService, service_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community service not found")
    previous = row.verification_status
    row.verification_status = "outdated"
    row.updated_by_user_id = ctx.user_id
    row.verification_notes = _optional_text(data.notes)
    session.add(row)
    _append_history(
        session,
        ctx,
        row,
        action="flagged_outdated",
        from_status=previous,
        to_status="outdated",
        notes=data.notes,
    )
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.COMMUNITY_SERVICE_FLAG_OUTDATED,
        row=row,
        summary="Community service listing flagged outdated",
    )
    return _admin_out(row)


def deactivate_community_service(
    session: Session,
    ctx: OrganisationContext,
    service_id: uuid.UUID,
    data: CommunityServiceDeactivateBody,
) -> CommunityServiceAdminOut:
    require_catalogue_writer(ctx)
    row = session.get(CommunityService, service_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community service not found")
    previous = row.verification_status
    row.verification_status = "inactive"
    row.is_published = False
    row.updated_by_user_id = ctx.user_id
    row.verification_notes = _optional_text(data.notes)
    session.add(row)
    _append_history(
        session,
        ctx,
        row,
        action="deactivated",
        from_status=previous,
        to_status="inactive",
        notes=data.notes,
    )
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.COMMUNITY_SERVICE_DEACTIVATE,
        row=row,
        summary="Community service listing deactivated",
    )
    return _admin_out(row)


def list_verification_history(
    session: Session,
    ctx: OrganisationContext,
    service_id: uuid.UUID,
) -> dict[str, list[VerificationEventOut]]:
    require_catalogue_writer(ctx)
    row = session.get(CommunityService, service_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community service not found")
    events = list(
        session.scalars(
            select(CommunityServiceVerificationEvent)
            .where(
                CommunityServiceVerificationEvent.organisation_id == ctx.organisation_id,
                CommunityServiceVerificationEvent.service_id == service_id,
            )
            .order_by(CommunityServiceVerificationEvent.created_at.desc())
        )
    )
    return {"items": [VerificationEventOut.model_validate(event) for event in events]}


# --- Opportunities (unchanged F4.1 surface) ---


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
