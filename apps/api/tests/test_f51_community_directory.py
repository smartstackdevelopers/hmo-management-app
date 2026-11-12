"""F5.1 community directory: categories, verification, admin, tenant isolation."""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException
from pydantic import ValidationError

from app.db.models.enums import HMoreRole, MembershipStatus
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenant_portal import catalogue
from app.tenant_portal.schemas import (
    CommunityServiceDeactivateBody,
    CommunityServiceFlagBody,
    CommunityServiceUpdate,
    CommunityServiceVerifyBody,
    CommunityServiceWrite,
)
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


def test_alembic_head_is_f51() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261112_4600_f72"]
    rev = script.get_revision("20261110_3400_f51")
    assert rev is not None
    assert rev.down_revision == "20261110_3300_f46"
    f52 = script.get_revision("20261110_3500_f52")
    assert f52 is not None
    assert f52.down_revision == "20261110_3400_f51"


def test_tenant_out_schema_hides_verification_notes() -> None:
    from app.tenant_portal.schemas import CommunityServiceAdminOut, CommunityServiceOut

    assert "verification_notes" not in CommunityServiceOut.model_fields
    assert "verification_notes" in CommunityServiceAdminOut.model_fields
    assert "verified_at" in CommunityServiceOut.model_fields
    assert "verification_status" in CommunityServiceOut.model_fields


def test_write_schema_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        CommunityServiceWrite.model_validate(
            {
                "category": "food_bank",
                "name": "Local pantry",
                "verification_status": "verified",
            }
        )


def test_tenant_has_discover_but_not_catalogue_write() -> None:
    assert role_has_permission(HMoreRole.TENANT, Permission.SERVICES_DISCOVER)
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), user)
    with pytest.raises(HTTPException) as denied:
        catalogue.require_catalogue_writer(ctx)
    assert denied.value.status_code == 403


@pytest.mark.postgres
def test_directory_categories_search_pagination_and_details(db_session, unique_suffix: str) -> None:
    from sqlalchemy import select

    from app.db.models import CommunityService, Organisation, User

    org = Organisation(name="Dir Org", slug=f"f51-dir-{unique_suffix}")
    other = Organisation(name="Other", slug=f"f51-other-{unique_suffix}")
    user = User(
        email=f"tenant-{unique_suffix}@example.com",
        display_name="Tenant",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, other, user])
    db_session.flush()
    db_session.add_all(
        [
            CommunityService(
                organisation_id=org.id,
                category="food_bank",
                name=f"Alpha Food {unique_suffix}",
                description="Emergency parcels",
                address_line="1 High Street",
                opening_days="Mon–Fri",
                opening_hours="10:00–14:00",
                eligibility="Referral preferred",
                referral_requirements="Support worker referral",
                contact="food@example.org",
                service_instructions="Bring ID if available",
                verification_status="verified",
                is_published=True,
            ),
            CommunityService(
                organisation_id=org.id,
                category="kitchen",
                name=f"Beta Kitchen {unique_suffix}",
                opening_hours="12:00–13:00",
                verification_status="pending_verification",
                is_published=True,
            ),
            CommunityService(
                organisation_id=org.id,
                category="clothing_bank",
                name=f"Gamma Clothing {unique_suffix}",
                clothing_service_type="provides_clothing",
                verification_status="verified",
                is_published=True,
            ),
            CommunityService(
                organisation_id=org.id,
                category="food_bank",
                name=f"Draft Food {unique_suffix}",
                verification_status="pending_verification",
                is_published=False,
            ),
            CommunityService(
                organisation_id=org.id,
                category="food_bank",
                name=f"Inactive Food {unique_suffix}",
                verification_status="inactive",
                is_published=False,
            ),
            CommunityService(
                organisation_id=other.id,
                category="food_bank",
                name=f"Other Org Food {unique_suffix}",
                verification_status="verified",
                is_published=True,
            ),
        ]
    )
    db_session.flush()
    tenant = _ctx(HMoreRole.TENANT, org.id, user)

    categories = catalogue.list_service_categories(tenant)
    assert [item["id"] for item in categories["items"]][:3] == [
        "food_bank",
        "kitchen",
        "clothing_bank",
    ]

    page = catalogue.list_community_services(
        db_session, tenant, q=unique_suffix, category="food_bank", page=1, page_size=10
    )
    assert page.total == 1
    assert page.items[0].name == f"Alpha Food {unique_suffix}"
    assert page.items[0].opening_days == "Mon–Fri"
    assert page.items[0].referral_requirements == "Support worker referral"
    assert page.items[0].verification_status == "verified"
    assert not hasattr(page.items[0], "verification_notes") or "verification_notes" not in page.items[
        0
    ].model_dump()

    kitchens = catalogue.list_community_services(
        db_session, tenant, q=unique_suffix, category="kitchen"
    )
    assert [row.name for row in kitchens.items] == [f"Beta Kitchen {unique_suffix}"]
    assert kitchens.items[0].verification_status == "pending_verification"

    clothing = catalogue.list_community_services(
        db_session, tenant, q=unique_suffix, category="clothing_bank"
    )
    assert clothing.items[0].clothing_service_type == "provides_clothing"

    hours_filter = catalogue.list_community_services(
        db_session,
        tenant,
        q=unique_suffix,
        category=None,
        has_opening_hours=True,
    )
    assert {row.name for row in hours_filter.items} == {
        f"Alpha Food {unique_suffix}",
        f"Beta Kitchen {unique_suffix}",
    }

    paged = catalogue.list_community_services(
        db_session, tenant, q=unique_suffix, category=None, page=1, page_size=2
    )
    assert paged.page_size == 2
    assert paged.total == 3
    assert len(paged.items) == 2

    empty = catalogue.list_community_services(
        db_session, tenant, q="zzz-no-match", category=None
    )
    assert empty.total == 0
    assert empty.items == []

    detail = catalogue.get_community_service(db_session, tenant, page.items[0].id)
    assert detail.name == f"Alpha Food {unique_suffix}"
    assert detail.service_instructions == "Bring ID if available"

    draft = db_session.scalar(
        select(CommunityService).where(CommunityService.name == f"Draft Food {unique_suffix}")
    )
    assert draft is not None
    with pytest.raises(HTTPException) as missing:
        catalogue.get_community_service(db_session, tenant, draft.id)
    assert missing.value.status_code == 404


@pytest.mark.postgres
def test_admin_verification_workflow_and_security(db_session, unique_suffix: str) -> None:
    from app.db.models import CommunityService, Organisation, User

    org_a = Organisation(name="A", slug=f"f51-a-{unique_suffix}")
    org_b = Organisation(name="B", slug=f"f51-b-{unique_suffix}")
    admin = User(
        email=f"admin-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    tenant_user = User(
        email=f"ten-{unique_suffix}@example.com",
        display_name="Tenant",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, admin, tenant_user])
    db_session.flush()
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin)
    tenant_ctx = _ctx(HMoreRole.TENANT, org_a.id, tenant_user)

    created = catalogue.create_community_service(
        db_session,
        admin_ctx,
        CommunityServiceWrite(
            category="food_bank",
            name=f"City Pantry {unique_suffix}",
            address_line="2 Market Road",
            opening_days="Tue, Thu",
            opening_hours="09:00-12:00",
            eligibility="Local residents",
            referral_requirements=None,
            contact="pantry@example.org",
            information_source="Council directory 2026",
            is_published=False,
        ),
    )
    assert created.verification_status == "pending_verification"
    assert created.is_published is False
    assert created.created_by_user_id == admin.id

    # New listings are not tenant-visible until published.
    tenant_page = catalogue.list_community_services(
        db_session, tenant_ctx, q=unique_suffix, category="food_bank"
    )
    assert tenant_page.total == 0

    with pytest.raises(HTTPException) as tenant_denied:
        catalogue.verify_community_service(
            db_session, tenant_ctx, created.id, CommunityServiceVerifyBody()
        )
    assert tenant_denied.value.status_code == 403

    verified = catalogue.verify_community_service(
        db_session,
        admin_ctx,
        created.id,
        CommunityServiceVerifyBody(notes="Checked with provider", publish=True),
    )
    assert verified.verification_status == "verified"
    assert verified.is_published is True
    assert verified.verified_by_user_id == admin.id
    assert verified.verified_at is not None
    assert verified.verification_notes == "Checked with provider"

    visible = catalogue.list_community_services(
        db_session, tenant_ctx, q=unique_suffix, category="food_bank"
    )
    assert visible.total == 1
    assert "verification_notes" not in visible.items[0].model_dump()

    updated = catalogue.update_community_service(
        db_session,
        admin_ctx,
        created.id,
        CommunityServiceUpdate(opening_hours="10:00-13:00", eligibility="Photo ID helpful"),
    )
    assert updated.opening_hours == "10:00-13:00"
    assert updated.eligibility == "Photo ID helpful"
    assert updated.verification_status == "needs_review"

    outdated = catalogue.flag_outdated_community_service(
        db_session,
        admin_ctx,
        created.id,
        CommunityServiceFlagBody(notes="Hours changed on website"),
    )
    assert outdated.verification_status == "outdated"

    deactivated = catalogue.deactivate_community_service(
        db_session,
        admin_ctx,
        created.id,
        CommunityServiceDeactivateBody(notes="Service closed"),
    )
    assert deactivated.verification_status == "inactive"
    assert deactivated.is_published is False

    history = catalogue.list_verification_history(db_session, admin_ctx, created.id)
    actions = [item.action for item in history["items"]]
    assert "created" in actions
    assert "verified" in actions
    assert "flagged_outdated" in actions
    assert "deactivated" in actions

    # Org isolation: admin of org A cannot manage org B rows.
    foreign = CommunityService(
        organisation_id=org_b.id,
        category="kitchen",
        name=f"Foreign Kitchen {unique_suffix}",
        is_published=True,
        verification_status="verified",
    )
    db_session.add(foreign)
    db_session.flush()
    with pytest.raises(HTTPException) as iso:
        catalogue.get_community_service(db_session, admin_ctx, foreign.id, admin=True)
    assert iso.value.status_code == 404

    # Duplicate prevention
    catalogue.create_community_service(
        db_session,
        admin_ctx,
        CommunityServiceWrite(category="kitchen", name=f"Unique Kitchen {unique_suffix}"),
    )
    with pytest.raises(HTTPException) as dup:
        catalogue.create_community_service(
            db_session,
            admin_ctx,
            CommunityServiceWrite(category="kitchen", name=f"unique kitchen {unique_suffix}"),
        )
    assert dup.value.status_code == 409

    with pytest.raises(HTTPException) as bad_hours_category:
        catalogue.create_community_service(
            db_session,
            admin_ctx,
            CommunityServiceWrite(
                category="food_bank",
                name=f"Bad clothing type {unique_suffix}",
                clothing_service_type="provides_clothing",
            ),
        )
    assert bad_hours_category.value.status_code == 422

    admin_list = catalogue.list_admin_community_services(
        db_session,
        admin_ctx,
        q=unique_suffix,
        category=None,
        verification_status="inactive",
    )
    assert any(row.name == f"City Pantry {unique_suffix}" for row in admin_list.items)

    with pytest.raises(HTTPException) as landlord_denied:
        catalogue.create_community_service(
            db_session,
            _ctx(HMoreRole.LANDLORD, org_a.id, admin),
            CommunityServiceWrite(category="food_bank", name=f"Landlord attempt {unique_suffix}"),
        )
    assert landlord_denied.value.status_code == 403
