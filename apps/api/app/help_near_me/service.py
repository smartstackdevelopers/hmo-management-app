"""Postcode nearby search, service geocoding, and outdated listing reports."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import get_settings
from app.db.models.catalogue import CommunityService
from app.db.models.enums import HMoreRole
from app.db.models.help_near_me import (
    REPORT_REASONS,
    REPORT_STATUSES,
    CommunityServiceOutdatedReport,
    HelpNearMeSearchEvent,
)
from app.geocoding.service import extract_uk_postcode, geocode_postcode, normalize_uk_postcode
from app.help_near_me.schemas import (
    ManualCoordinatesBody,
    NearbySearchOut,
    NearbyServiceOut,
    OutdatedReportAdminUpdate,
    OutdatedReportOut,
    OutdatedReportPage,
    OutdatedReportWrite,
    PostcodeValidateOut,
    ServiceGeocodeOut,
)
from app.rbac.permissions import Permission
from app.tenant_portal.catalogue import require_catalogue_writer
from app.tenant_portal.schemas import COMMUNITY_CATEGORIES
from app.tenancy.context import OrganisationContext

EARTH_RADIUS_KM = 6371.0
OPEN_REPORT_STATUSES = frozenset(
    {"submitted", "under_review", "information_confirmed", "listing_updated"}
)


def _require_discover(ctx: OrganisationContext) -> None:
    if not ctx.authorization.has_permission(Permission.SERVICES_DISCOVER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {Permission.SERVICES_DISCOVER.value}",
        )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _purge_old_search_events(session: Session, *, retention_hours: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
    session.execute(delete(HelpNearMeSearchEvent).where(HelpNearMeSearchEvent.created_at < cutoff))


def _rate_limit_search(session: Session, ctx: OrganisationContext) -> None:
    settings = get_settings()
    _purge_old_search_events(session, retention_hours=settings.help_near_me_search_retention_hours)
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = session.scalar(
        select(func.count())
        .select_from(HelpNearMeSearchEvent)
        .where(
            HelpNearMeSearchEvent.organisation_id == ctx.organisation_id,
            HelpNearMeSearchEvent.user_id == ctx.user_id,
            HelpNearMeSearchEvent.created_at >= since,
        )
    ) or 0
    if int(count) >= settings.help_near_me_search_hourly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Help Near Me search rate limit exceeded. Try again later.",
        )


def _rate_limit_report(session: Session, ctx: OrganisationContext) -> None:
    settings = get_settings()
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = session.scalar(
        select(func.count())
        .select_from(CommunityServiceOutdatedReport)
        .where(
            CommunityServiceOutdatedReport.organisation_id == ctx.organisation_id,
            CommunityServiceOutdatedReport.reporter_user_id == ctx.user_id,
            CommunityServiceOutdatedReport.created_at >= since,
        )
    ) or 0
    if int(count) >= settings.help_near_me_report_hourly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Report rate limit exceeded. Try again later.",
        )


def validate_postcode(ctx: OrganisationContext, postcode: str) -> PostcodeValidateOut:
    _require_discover(ctx)
    result = geocode_postcode(postcode)
    return PostcodeValidateOut(
        postcode=result.postcode,
        latitude=result.latitude,
        longitude=result.longitude,
        provider=result.provider,
    )


def search_nearby(
    session: Session,
    ctx: OrganisationContext,
    *,
    postcode: str,
    category: str | None = None,
    radius_km: float | None = None,
    sort: str = "distance",
    page: int = 1,
    page_size: int = 20,
) -> NearbySearchOut:
    _require_discover(ctx)
    if category is not None and category not in COMMUNITY_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category")
    if sort not in {"distance", "name"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid sort")

    settings = get_settings()
    max_radius = settings.help_near_me_max_radius_km
    effective_radius = settings.help_near_me_default_radius_km if radius_km is None else float(radius_km)
    if effective_radius < 0.5 or effective_radius > max_radius:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"radius_km must be between 0.5 and {max_radius}",
        )

    _rate_limit_search(session, ctx)
    geo = geocode_postcode(postcode)
    session.add(
        HelpNearMeSearchEvent(
            organisation_id=ctx.organisation_id,
            user_id=ctx.user_id,
            postcode_normalised=normalize_uk_postcode(geo.postcode),
        )
    )
    session.flush()

    # Bounding-box prefilter then exact Haversine (no invented coordinates).
    lat_delta = effective_radius / 111.0
    lon_delta = effective_radius / max(0.01, 111.0 * math.cos(math.radians(geo.latitude)))
    filters = [
        CommunityService.organisation_id == ctx.organisation_id,
        CommunityService.is_published.is_(True),
        CommunityService.verification_status != "inactive",
        CommunityService.latitude.is_not(None),
        CommunityService.longitude.is_not(None),
        CommunityService.latitude.between(geo.latitude - lat_delta, geo.latitude + lat_delta),
        CommunityService.longitude.between(geo.longitude - lon_delta, geo.longitude + lon_delta),
    ]
    if category:
        filters.append(CommunityService.category == category)

    rows = list(session.scalars(select(CommunityService).where(*filters)))
    scored: list[tuple[float, CommunityService]] = []
    for row in rows:
        assert row.latitude is not None and row.longitude is not None
        distance = _haversine_km(geo.latitude, geo.longitude, row.latitude, row.longitude)
        if distance <= effective_radius + 1e-9:
            scored.append((distance, row))

    if sort == "name":
        scored.sort(key=lambda item: (item[1].name.lower(), item[0]))
    else:
        scored.sort(key=lambda item: (item[0], item[1].name.lower()))

    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = len(scored)
    start = (page - 1) * page_size
    page_rows = scored[start : start + page_size]

    items: list[NearbyServiceOut] = []
    for distance, row in page_rows:
        items.append(
            NearbyServiceOut(
                id=row.id,
                category=row.category,
                name=row.name,
                description=row.description,
                address_line=row.address_line,
                opening_days=row.opening_days,
                opening_hours=row.opening_hours,
                eligibility=row.eligibility,
                referral_requirements=row.referral_requirements,
                contact=row.contact,
                service_instructions=row.service_instructions,
                clothing_service_type=row.clothing_service_type,
                verification_status=row.verification_status,
                verified_at=row.verified_at,
                updated_at=row.updated_at,
                latitude=float(row.latitude),
                longitude=float(row.longitude),
                distance_km=round(distance, 2),
                distance_miles=round(distance * 0.621371, 2),
            )
        )

    return NearbySearchOut(
        postcode=geo.postcode,
        latitude=geo.latitude,
        longitude=geo.longitude,
        radius_km=effective_radius,
        sort=sort,
        page=page,
        page_size=page_size,
        total=total,
        items=items,
    )


def geocode_service_from_address(
    session: Session,
    ctx: OrganisationContext,
    service_id: uuid.UUID,
) -> ServiceGeocodeOut:
    """Geocode a service using a UK postcode found in its address. Never invents coords."""
    require_catalogue_writer(ctx)
    row = session.get(CommunityService, service_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community service not found")
    postcode = extract_uk_postcode(row.address_line)
    if postcode is None:
        row.geocode_status = "failed"
        row.geocode_provider = None
        row.geocoded_at = datetime.now(timezone.utc)
        session.add(row)
        session.flush()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Address does not contain a recognisable UK postcode",
        )
    try:
        geo = geocode_postcode(postcode)
    except HTTPException:
        row.geocode_status = "failed"
        row.geocode_provider = get_settings().geocoding_provider
        row.geocoded_at = datetime.now(timezone.utc)
        session.add(row)
        session.flush()
        raise
    row.latitude = geo.latitude
    row.longitude = geo.longitude
    row.geocode_provider = geo.provider
    row.geocode_status = "verified"
    row.geocoded_at = datetime.now(timezone.utc)
    row.updated_by_user_id = ctx.user_id
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.COMMUNITY_SERVICE_GEOCODE,
        resource_type="community_service",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Community service geocoded from address postcode",
        metadata={"provider": geo.provider, "postcode": geo.postcode},
    )
    return ServiceGeocodeOut(
        id=row.id,
        latitude=row.latitude,
        longitude=row.longitude,
        geocode_status=row.geocode_status,
        geocode_provider=row.geocode_provider,
        geocoded_at=row.geocoded_at,
    )


def set_manual_coordinates(
    session: Session,
    ctx: OrganisationContext,
    service_id: uuid.UUID,
    body: ManualCoordinatesBody,
) -> ServiceGeocodeOut:
    require_catalogue_writer(ctx)
    row = session.get(CommunityService, service_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community service not found")
    row.latitude = body.latitude
    row.longitude = body.longitude
    row.geocode_provider = "manual"
    row.geocode_status = "manual"
    row.geocoded_at = datetime.now(timezone.utc)
    row.updated_by_user_id = ctx.user_id
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.COMMUNITY_SERVICE_GEOCODE,
        resource_type="community_service",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Community service coordinates set manually",
        metadata={"provider": "manual"},
    )
    return ServiceGeocodeOut(
        id=row.id,
        latitude=row.latitude,
        longitude=row.longitude,
        geocode_status=row.geocode_status,
        geocode_provider=row.geocode_provider,
        geocoded_at=row.geocoded_at,
    )


def submit_outdated_report(
    session: Session,
    ctx: OrganisationContext,
    body: OutdatedReportWrite,
) -> OutdatedReportOut:
    _require_discover(ctx)
    if ctx.role not in {HMoreRole.TENANT, HMoreRole.SUPPORT_WORKER, HMoreRole.ORGANISATION_ADMIN, HMoreRole.SUPER_ADMIN}:
        # Landlords / contractors do not file tenant directory reports unless they have discover.
        pass
    if body.reason not in REPORT_REASONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid report reason")
    service = session.get(CommunityService, body.service_id)
    if (
        service is None
        or service.organisation_id != ctx.organisation_id
        or not service.is_published
        or service.verification_status == "inactive"
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community service not found")

    _rate_limit_report(session, ctx)

    # Duplicate open report for same user+service+reason within 24h.
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    duplicate = session.scalar(
        select(CommunityServiceOutdatedReport)
        .where(
            CommunityServiceOutdatedReport.organisation_id == ctx.organisation_id,
            CommunityServiceOutdatedReport.service_id == body.service_id,
            CommunityServiceOutdatedReport.reporter_user_id == ctx.user_id,
            CommunityServiceOutdatedReport.reason == body.reason,
            CommunityServiceOutdatedReport.status.in_(tuple(OPEN_REPORT_STATUSES)),
            CommunityServiceOutdatedReport.created_at >= since,
        )
        .limit(1)
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an open report for this service and reason",
        )

    details = (body.details or "").strip() or None
    row = CommunityServiceOutdatedReport(
        organisation_id=ctx.organisation_id,
        service_id=body.service_id,
        reporter_user_id=ctx.user_id,
        reason=body.reason,
        details=details,
        status="submitted",
    )
    session.add(row)
    # A report creates a review request — never auto-verifies or deletes.
    if service.verification_status == "verified":
        previous = service.verification_status
        service.verification_status = "needs_review"
        service.updated_by_user_id = ctx.user_id
        session.add(service)
        from app.db.models.catalogue import CommunityServiceVerificationEvent

        session.add(
            CommunityServiceVerificationEvent(
                organisation_id=ctx.organisation_id,
                service_id=service.id,
                from_status=previous,
                to_status="needs_review",
                action="tenant_report",
                notes=f"Tenant report: {body.reason}",
                actor_user_id=ctx.user_id,
            )
        )
    session.flush()
    record_event(
        session,
        action=audit_events.COMMUNITY_SERVICE_REPORT_SUBMIT,
        resource_type="community_service_outdated_report",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Outdated community service report submitted",
        metadata={"service_id": str(body.service_id), "reason": body.reason},
    )
    return _report_out(row, service=service, include_reporter=False)


def list_own_reports(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int = 1,
    page_size: int = 20,
) -> OutdatedReportPage:
    _require_discover(ctx)
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    filters = [
        CommunityServiceOutdatedReport.organisation_id == ctx.organisation_id,
        CommunityServiceOutdatedReport.reporter_user_id == ctx.user_id,
    ]
    total = session.scalar(
        select(func.count()).select_from(CommunityServiceOutdatedReport).where(*filters)
    ) or 0
    rows = list(
        session.scalars(
            select(CommunityServiceOutdatedReport)
            .where(*filters)
            .order_by(CommunityServiceOutdatedReport.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return OutdatedReportPage(
        items=[_report_out(row, include_reporter=False) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def list_admin_reports(
    session: Session,
    ctx: OrganisationContext,
    *,
    status_filter: str | None,
    category: str | None,
    q: str | None,
    page: int = 1,
    page_size: int = 25,
) -> OutdatedReportPage:
    require_catalogue_writer(ctx)
    if status_filter is not None and status_filter not in REPORT_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid status")
    if category is not None and category not in COMMUNITY_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category")
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    stmt = (
        select(CommunityServiceOutdatedReport, CommunityService)
        .join(CommunityService, CommunityService.id == CommunityServiceOutdatedReport.service_id)
        .where(CommunityServiceOutdatedReport.organisation_id == ctx.organisation_id)
    )
    if status_filter:
        stmt = stmt.where(CommunityServiceOutdatedReport.status == status_filter)
    if category:
        stmt = stmt.where(CommunityService.category == category)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                CommunityService.name.ilike(pattern),
                CommunityServiceOutdatedReport.details.ilike(pattern),
                CommunityServiceOutdatedReport.reason.ilike(pattern),
            )
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    pairs = list(
        session.execute(
            stmt.order_by(CommunityServiceOutdatedReport.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    items = [
        _report_out(report, service=service, include_reporter=True) for report, service in pairs
    ]
    return OutdatedReportPage(items=items, page=page, page_size=page_size, total=total)


def get_admin_report(
    session: Session, ctx: OrganisationContext, report_id: uuid.UUID
) -> OutdatedReportOut:
    require_catalogue_writer(ctx)
    row = session.get(CommunityServiceOutdatedReport, report_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    service = session.get(CommunityService, row.service_id)
    return _report_out(row, service=service, include_reporter=True)


def update_admin_report(
    session: Session,
    ctx: OrganisationContext,
    report_id: uuid.UUID,
    body: OutdatedReportAdminUpdate,
) -> OutdatedReportOut:
    require_catalogue_writer(ctx)
    if body.status not in REPORT_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid status")
    row = session.get(CommunityServiceOutdatedReport, report_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    row.status = body.status
    if body.resolution_notes is not None:
        row.resolution_notes = body.resolution_notes.strip() or None
    row.reviewed_by_user_id = ctx.user_id
    row.reviewed_at = datetime.now(timezone.utc)
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.COMMUNITY_SERVICE_REPORT_MODERATE,
        resource_type="community_service_outdated_report",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Community service outdated report moderated",
        metadata={"status": row.status, "service_id": str(row.service_id)},
    )
    service = session.get(CommunityService, row.service_id)
    return _report_out(row, service=service, include_reporter=True)


def _report_out(
    row: CommunityServiceOutdatedReport,
    *,
    service: CommunityService | None = None,
    include_reporter: bool,
) -> OutdatedReportOut:
    return OutdatedReportOut(
        id=row.id,
        service_id=row.service_id,
        reason=row.reason,
        details=row.details,
        status=row.status,
        resolution_notes=row.resolution_notes,
        reviewed_by_user_id=row.reviewed_by_user_id,
        reviewed_at=row.reviewed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        reporter_user_id=row.reporter_user_id if include_reporter else None,
        service_name=service.name if service else None,
        service_category=service.category if service else None,
    )
