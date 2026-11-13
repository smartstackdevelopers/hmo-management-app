"""F5.2 Help Near Me: postcode geocoding, nearby search, reports, moderation."""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.db.models.enums import HMoreRole, MembershipStatus
from app.geocoding.service import (
    GeocodeResult,
    looks_like_uk_postcode,
    normalize_uk_postcode,
)
from app.help_near_me import service as help_near_me
from app.help_near_me.schemas import OutdatedReportAdminUpdate, OutdatedReportWrite
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def _ctx(role: HMoreRole, organisation_id, user) -> OrganisationContext:
    authz = AuthorizationContext(
        user=user,
        memberships=[
            MembershipView(
                membership_id=uuid.uuid4(),
                role=role,
                organisation_id=organisation_id,
                status=MembershipStatus.ACTIVE,
            )
        ],
        active_organisation_id=organisation_id,
        active_role=role,
    )
    return OrganisationContext(
        user=user,
        organisation_id=organisation_id,
        role=role,
        authorization=authz,
    )


def test_alembic_head_is_f52() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261121_5700_f89"]
    rev = script.get_revision("20261110_3500_f52")
    assert rev is not None
    assert rev.down_revision == "20261110_3400_f51"
    f53 = script.get_revision("20261110_3600_f53")
    assert f53 is not None
    assert f53.down_revision == "20261110_3500_f52"


def test_normalize_postcode_spaces_and_case() -> None:
    assert normalize_uk_postcode("sw1a1aa") == "SW1A 1AA"
    assert normalize_uk_postcode("  Sw1A  1Aa ") == "SW1A 1AA"
    assert looks_like_uk_postcode("B1 1AA")
    assert not looks_like_uk_postcode("not-a-postcode")


def test_pattern_alone_does_not_geocode_without_provider() -> None:
    """Shape-valid strings still require a live provider response."""
    assert looks_like_uk_postcode("ZZ99 9ZZ")
    with patch(
        "app.geocoding.service._geocode_postcodes_io",
        side_effect=HTTPException(status_code=422, detail="Postcode not found"),
    ):
        with pytest.raises(HTTPException) as exc:
            from app.geocoding.service import geocode_postcode

            geocode_postcode("ZZ99 9ZZ")
        assert exc.value.status_code == 422


def test_tenant_has_discover_permission() -> None:
    assert role_has_permission(HMoreRole.TENANT, Permission.SERVICES_DISCOVER)


def test_validate_postcode_uses_provider_result() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), user)
    fake = GeocodeResult(
        postcode="SW1A 1AA",
        latitude=51.501,
        longitude=-0.142,
        provider="postcodes_io",
    )
    with patch("app.help_near_me.service.geocode_postcode", return_value=fake):
        out = help_near_me.validate_postcode(ctx, "sw1a1aa")
    assert out.postcode == "SW1A 1AA"
    assert out.latitude == 51.501
    assert out.provider == "postcodes_io"


@pytest.mark.postgres
def test_nearby_search_distance_filters_and_reports(db_session, unique_suffix: str) -> None:
    from app.db.models import CommunityService, Organisation, User
    from app.tenant_portal import catalogue
    from app.tenant_portal.schemas import CommunityServiceWrite

    org = Organisation(name="Near Org", slug=f"f52-near-{unique_suffix}")
    other = Organisation(name="Other", slug=f"f52-other-{unique_suffix}")
    admin = User(
        email=f"admin-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    tenant = User(
        email=f"tenant-{unique_suffix}@example.com",
        display_name="Tenant",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, other, admin, tenant])
    db_session.flush()
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin)
    tenant_ctx = _ctx(HMoreRole.TENANT, org.id, tenant)

    near_food = catalogue.create_community_service(
        db_session,
        admin_ctx,
        CommunityServiceWrite(
            category="food_bank",
            name=f"Near Food {unique_suffix}",
            address_line="1 Test Street, SW1A 1AA",
            opening_hours="10:00-12:00",
            eligibility="Local residents",
            is_published=True,
        ),
    )
    near_row = db_session.get(CommunityService, near_food.id)
    assert near_row is not None
    near_row.latitude = 51.5014
    near_row.longitude = -0.1419
    near_row.geocode_status = "verified"
    near_row.geocode_provider = "postcodes_io"
    near_row.verification_status = "verified"
    db_session.add(near_row)

    kitchen = catalogue.create_community_service(
        db_session,
        admin_ctx,
        CommunityServiceWrite(
            category="kitchen",
            name=f"Near Kitchen {unique_suffix}",
            address_line="2 Test Street, SW1A 1AA",
            is_published=True,
        ),
    )
    kitchen_row = db_session.get(CommunityService, kitchen.id)
    assert kitchen_row is not None
    kitchen_row.latitude = 51.5020
    kitchen_row.longitude = -0.1425
    kitchen_row.geocode_status = "verified"
    kitchen_row.verification_status = "pending_verification"
    db_session.add(kitchen_row)

    clothing = catalogue.create_community_service(
        db_session,
        admin_ctx,
        CommunityServiceWrite(
            category="clothing_bank",
            name=f"Near Clothing {unique_suffix}",
            clothing_service_type="provides_clothing",
            is_published=True,
        ),
    )
    clothing_row = db_session.get(CommunityService, clothing.id)
    assert clothing_row is not None
    clothing_row.latitude = 51.5030
    clothing_row.longitude = -0.1430
    clothing_row.geocode_status = "verified"
    clothing_row.verification_status = "verified"
    db_session.add(clothing_row)

    far = catalogue.create_community_service(
        db_session,
        admin_ctx,
        CommunityServiceWrite(
            category="food_bank",
            name=f"Far Food {unique_suffix}",
            is_published=True,
        ),
    )
    far_row = db_session.get(CommunityService, far.id)
    assert far_row is not None
    far_row.latitude = 53.4808
    far_row.longitude = -2.2426
    far_row.geocode_status = "verified"
    far_row.verification_status = "verified"
    db_session.add(far_row)

    inactive = catalogue.create_community_service(
        db_session,
        admin_ctx,
        CommunityServiceWrite(
            category="food_bank",
            name=f"Inactive Near {unique_suffix}",
            is_published=False,
        ),
    )
    inactive_row = db_session.get(CommunityService, inactive.id)
    assert inactive_row is not None
    inactive_row.latitude = 51.5015
    inactive_row.longitude = -0.1420
    inactive_row.verification_status = "inactive"
    db_session.add(inactive_row)

    other_svc = CommunityService(
        organisation_id=other.id,
        category="food_bank",
        name=f"Other Org Near {unique_suffix}",
        is_published=True,
        verification_status="verified",
        latitude=51.5014,
        longitude=-0.1419,
        geocode_status="verified",
    )
    db_session.add(other_svc)
    db_session.flush()

    fake_geo = GeocodeResult(
        postcode="SW1A 1AA",
        latitude=51.5014,
        longitude=-0.1419,
        provider="postcodes_io",
    )
    with patch("app.help_near_me.service.geocode_postcode", return_value=fake_geo):
        page = help_near_me.search_nearby(
            db_session,
            tenant_ctx,
            postcode="sw1a 1aa",
            radius_km=5,
            sort="distance",
        )
    names = [item.name for item in page.items]
    assert f"Near Food {unique_suffix}" in names
    assert f"Near Kitchen {unique_suffix}" in names
    assert f"Near Clothing {unique_suffix}" in names
    assert f"Far Food {unique_suffix}" not in names
    assert f"Inactive Near {unique_suffix}" not in names
    assert f"Other Org Near {unique_suffix}" not in names
    assert page.items[0].distance_km <= page.items[-1].distance_km
    kitchen_hit = next(item for item in page.items if "Kitchen" in item.name)
    assert kitchen_hit.verification_status == "pending_verification"

    with patch("app.help_near_me.service.geocode_postcode", return_value=fake_geo):
        food_only = help_near_me.search_nearby(
            db_session,
            tenant_ctx,
            postcode="SW1A 1AA",
            category="food_bank",
            radius_km=5,
        )
    assert all(item.category == "food_bank" for item in food_only.items)
    assert f"Far Food {unique_suffix}" not in [item.name for item in food_only.items]

    with patch("app.help_near_me.service.geocode_postcode", return_value=fake_geo):
        tight = help_near_me.search_nearby(
            db_session,
            tenant_ctx,
            postcode="SW1A 1AA",
            radius_km=0.5,
        )
    assert tight.total >= 1

    with patch("app.help_near_me.service.geocode_postcode", return_value=fake_geo):
        empty = help_near_me.search_nearby(
            db_session,
            tenant_ctx,
            postcode="SW1A 1AA",
            category="local_service",
            radius_km=5,
        )
    assert empty.total == 0

    report = help_near_me.submit_outdated_report(
        db_session,
        tenant_ctx,
        OutdatedReportWrite(
            service_id=near_food.id,
            reason="opening_hours_incorrect",
            details="Board shows different hours",
        ),
    )
    assert report.status == "submitted"
    refreshed = db_session.get(CommunityService, near_food.id)
    assert refreshed is not None
    assert refreshed.verification_status == "needs_review"

    with pytest.raises(HTTPException) as dup:
        help_near_me.submit_outdated_report(
            db_session,
            tenant_ctx,
            OutdatedReportWrite(
                service_id=near_food.id,
                reason="opening_hours_incorrect",
            ),
        )
    assert dup.value.status_code == 409

    with pytest.raises(HTTPException) as denied:
        help_near_me.list_admin_reports(
            db_session,
            tenant_ctx,
            status_filter=None,
            category=None,
            q=None,
        )
    assert denied.value.status_code == 403

    admin_page = help_near_me.list_admin_reports(
        db_session,
        admin_ctx,
        status_filter="submitted",
        category="food_bank",
        q=unique_suffix,
    )
    assert admin_page.total >= 1
    moderated = help_near_me.update_admin_report(
        db_session,
        admin_ctx,
        report.id,
        OutdatedReportAdminUpdate(status="under_review", resolution_notes="Checking provider"),
    )
    assert moderated.status == "under_review"
    assert moderated.reviewed_by_user_id == admin.id


def test_geocode_disabled_returns_503() -> None:
    from app.core.config import Settings
    from app.geocoding.service import geocode_postcode

    settings = Settings(geocoding_provider="disabled")
    with pytest.raises(HTTPException) as exc:
        geocode_postcode("SW1A 1AA", settings=settings)
    assert exc.value.status_code == 503


def test_haversine_known_distance() -> None:
    # Roughly 1 degree latitude ≈ 111 km
    distance = help_near_me._haversine_km(51.0, 0.0, 52.0, 0.0)
    assert 110 < distance < 112

