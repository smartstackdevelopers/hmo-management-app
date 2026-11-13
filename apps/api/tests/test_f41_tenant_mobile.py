"""F4.1 tenant self profile, housing assignment, and catalogues.

PostgreSQL tests insert rows inside the test transaction. They do not seed catalogues.
"""

from __future__ import annotations

import inspect
import uuid
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException
from pydantic import ValidationError

from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenant_portal.catalogue import require_catalogue_writer
from app.tenant_portal.documents import assert_tenant_submission_type, upload_own_document
from app.tenant_portal.profile import get_own_housing
from app.tenant_portal.schemas import (
    HousingPropertyOut,
    HousingRoomOut,
    TenantSelfOut,
    TenantSelfUpdate,
)
from app.tenancy.context import OrganisationContext


def test_alembic_head_revises_f41_tenant_mobile() -> None:
    """F4.1 stays in the chain through F4.6; F5.1 revises F4.6 as the single head."""
    from pathlib import Path

    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert heads == ["20261122_5800_f811"]
    f43 = script.get_revision("20261110_3000_f43")
    assert f43 is not None
    assert f43.down_revision == "20261110_2900_f41"
    f45 = script.get_revision("20261110_3200_f45")
    assert f45 is not None
    assert f45.down_revision == "20261110_3000_f43"
    f46 = script.get_revision("20261110_3300_f46")
    assert f46 is not None
    assert f46.down_revision == "20261110_3200_f45"
    f51 = script.get_revision("20261110_3400_f51")
    assert f51 is not None
    assert f51.down_revision == "20261110_3300_f46"
    f52 = script.get_revision("20261110_3500_f52")
    assert f52 is not None
    assert f52.down_revision == "20261110_3400_f51"


def test_self_profile_schema_hides_staff_notes() -> None:
    assert "notes" not in TenantSelfOut.model_fields
    assert "consent_notes" not in TenantSelfOut.model_fields
    assert "needs_goals" not in TenantSelfOut.model_fields
    assert "notes" not in HousingPropertyOut.model_fields
    assert "notes" not in HousingRoomOut.model_fields


def test_self_patch_allows_only_preferred_name_and_phone() -> None:
    body = TenantSelfUpdate.model_validate({"preferred_name": "Amina", "phone": "07000 000000"})
    assert body.model_dump(exclude_unset=True) == {
        "preferred_name": "Amina",
        "phone": "07000 000000",
    }
    with pytest.raises(ValidationError):
        TenantSelfUpdate.model_validate(
            {
                "preferred_name": "Amina",
                "notes": "staff note",
                "assigned_property_id": str(uuid.uuid4()),
            }
        )
    with pytest.raises(ValidationError):
        TenantSelfUpdate.model_validate({"consent_notes": "no", "needs_goals": "no", "email": "a@b.c"})


def test_tenant_cannot_write_catalogues_or_gain_document_upload() -> None:
    ctx = _ctx(HMoreRole.TENANT)
    with pytest.raises(HTTPException) as exc:
        require_catalogue_writer(ctx)
    assert exc.value.status_code == 403
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.ORGANISATION_SETTINGS_MANAGE)
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.ORGANISATIONS_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.DOCUMENTS_UPLOAD)
    assert role_has_permission(HMoreRole.TENANT, Permission.SERVICES_DISCOVER)
    assert role_has_permission(HMoreRole.TENANT, Permission.JOBS_DISCOVER)
    assert role_has_permission(HMoreRole.TENANT, Permission.TRAINING_DISCOVER)


def test_tenant_document_upload_rejects_non_image_and_non_pdf() -> None:
    with pytest.raises(HTTPException) as exc:
        assert_tenant_submission_type(b"plain text", "text/plain")
    assert exc.value.status_code == 400
    assert_tenant_submission_type(b"%PDF-1.4 test", "application/pdf")
    assert_tenant_submission_type(b"\x89PNG\r\n\x1a\nrest", "image/png")
    params = inspect.signature(upload_own_document).parameters
    assert "tenant_id" not in params
    assert "category_id" not in params
    assert "tenant_id" not in inspect.signature(get_own_housing).parameters


def _ctx(role: HMoreRole, org_id: uuid.UUID | None = None, user: object | None = None) -> OrganisationContext:
    organisation_id = org_id or uuid.uuid4()
    actor = user or SimpleNamespace(
        id=uuid.uuid4(),
        authorization_version=1,
        external_subject=f"auth0|{uuid.uuid4()}",
        email="u@example.com",
        display_name="U",
    )
    authz = AuthorizationContext(
        user=actor,  # type: ignore[arg-type]
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
        user=actor,  # type: ignore[arg-type]
        organisation_id=organisation_id,
        role=role,
        authorization=authz,
    )


@pytest.mark.postgres
def test_tenant_can_patch_own_name_and_phone_only(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, Tenant, User
    from app.records.schemas import TenantUpdate
    from app.records.tenant_service import update_tenant
    from app.tenant_portal.profile import update_own_profile

    org = Organisation(name="Org", slug=f"f41-self-{unique_suffix}")
    user = User(
        email=f"tenant-{unique_suffix}@example.com",
        display_name="Tenant",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, user])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id,
        user_id=user.id,
        preferred_name="Before",
        phone="111",
        notes="keep-me",
        needs_goals="private",
        consent_notes="private-consent",
        status=RecordStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.flush()
    ctx = _ctx(HMoreRole.TENANT, org.id, user)

    updated = update_own_profile(
        db_session,
        ctx,
        TenantSelfUpdate(preferred_name="After", phone="222"),
    )
    assert updated.preferred_name == "After"
    assert updated.phone == "222"
    assert not hasattr(updated, "notes") or "notes" not in updated.model_fields_set and "notes" not in TenantSelfOut.model_fields
    db_session.refresh(tenant)
    assert tenant.notes == "keep-me"
    assert tenant.needs_goals == "private"
    assert tenant.consent_notes == "private-consent"

    with pytest.raises(HTTPException) as denied:
        update_tenant(
            db_session,
            ctx,
            tenant.id,
            TenantUpdate(notes="changed", assigned_property_id=uuid.uuid4()),
        )
    assert denied.value.status_code == 403
    db_session.refresh(tenant)
    assert tenant.notes == "keep-me"
    assert tenant.assigned_property_id is None


@pytest.mark.postgres
def test_housing_endpoint_returns_only_the_callers_assignment(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, Property, Room, Tenant, User
    from app.records.schemas import TenantUpdate
    from app.records.tenant_service import update_tenant

    org = Organisation(name="Org", slug=f"f41-house-{unique_suffix}")
    user_a = User(
        email=f"a-{unique_suffix}@example.com",
        display_name="A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    user_b = User(
        email=f"b-{unique_suffix}@example.com",
        display_name="B",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    admin = User(
        email=f"admin-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, user_a, user_b, admin])
    db_session.flush()
    prop = Property(
        organisation_id=org.id,
        name="Assigned house",
        address_line1="1 Test Street",
        address_line2=None,
        city="Birmingham",
        postcode="B1 1AA",
        notes="staff only note",
    )
    other_prop = Property(
        organisation_id=org.id,
        name="Other house",
        address_line1="9 Other Street",
        city="Birmingham",
        postcode="B2 2BB",
    )
    db_session.add_all([prop, other_prop])
    db_session.flush()
    room = Room(organisation_id=org.id, property_id=prop.id, label="Room 2", floor_label="1", notes="room note")
    other_room = Room(organisation_id=org.id, property_id=other_prop.id, label="Room 9", floor_label="2")
    db_session.add_all([room, other_room])
    db_session.flush()
    tenant_a = Tenant(
        organisation_id=org.id,
        user_id=user_a.id,
        preferred_name="A",
        tenancy_reference=f"REF-A-{unique_suffix}",
        status=RecordStatus.ACTIVE,
    )
    tenant_b = Tenant(
        organisation_id=org.id,
        user_id=user_b.id,
        preferred_name="B",
        tenancy_reference=f"REF-B-{unique_suffix}",
        status=RecordStatus.ACTIVE,
    )
    db_session.add_all([tenant_a, tenant_b])
    db_session.flush()

    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin)
    with pytest.raises(HTTPException) as mismatch:
        update_tenant(
            db_session,
            admin_ctx,
            tenant_b.id,
            TenantUpdate(assigned_property_id=prop.id, assigned_room_id=other_room.id),
        )
    assert mismatch.value.status_code == 400

    update_tenant(
        db_session,
        admin_ctx,
        tenant_b.id,
        TenantUpdate(assigned_property_id=prop.id, assigned_room_id=room.id),
    )
    db_session.refresh(tenant_b)
    assert tenant_b.assigned_property_id == prop.id
    assert tenant_b.assigned_room_id == room.id

    housing_a = get_own_housing(db_session, _ctx(HMoreRole.TENANT, org.id, user_a))
    housing_b = get_own_housing(db_session, _ctx(HMoreRole.TENANT, org.id, user_b))
    assert housing_a.property is None
    assert housing_a.room is None
    assert housing_a.tenancy_reference == tenant_a.tenancy_reference
    assert housing_b.tenancy_reference == tenant_b.tenancy_reference
    assert housing_b.property is not None
    assert housing_b.property.address_line1 == "1 Test Street"
    assert housing_b.room is not None
    assert housing_b.room.label == "Room 2"
    dumped = housing_b.model_dump()
    assert "notes" not in dumped["property"]
    assert "notes" not in dumped["room"]
    assert dumped["property"]["id"] != other_prop.id


@pytest.mark.postgres
def test_catalogues_hide_unpublished_and_other_organisations(db_session, unique_suffix: str) -> None:
    from app.db.models import CommunityService, OpportunityListing, Organisation, User
    from app.tenant_portal.catalogue import list_community_services, list_opportunities

    org_a = Organisation(name="A", slug=f"f41-cat-a-{unique_suffix}")
    org_b = Organisation(name="B", slug=f"f41-cat-b-{unique_suffix}")
    user = User(
        email=f"reader-{unique_suffix}@example.com",
        display_name="Reader",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, user])
    db_session.flush()
    db_session.add_all(
        [
            CommunityService(
                organisation_id=org_a.id,
                category="local_service",
                name=f"Published service {unique_suffix}",
                is_published=True,
            ),
            CommunityService(
                organisation_id=org_a.id,
                category="kitchen",
                name=f"Draft service {unique_suffix}",
                is_published=False,
            ),
            CommunityService(
                organisation_id=org_b.id,
                category="local_service",
                name=f"Other org service {unique_suffix}",
                is_published=True,
            ),
            OpportunityListing(
                organisation_id=org_a.id,
                kind="job",
                title=f"Published opening {unique_suffix}",
                is_published=True,
            ),
            OpportunityListing(
                organisation_id=org_a.id,
                kind="job",
                title=f"Draft opening {unique_suffix}",
                is_published=False,
            ),
            OpportunityListing(
                organisation_id=org_a.id,
                kind="training",
                title=f"Published course {unique_suffix}",
                is_published=True,
            ),
            OpportunityListing(
                organisation_id=org_b.id,
                kind="job",
                title=f"Other org opening {unique_suffix}",
                is_published=True,
            ),
        ]
    )
    db_session.flush()
    ctx = _ctx(HMoreRole.TENANT, org_a.id, user)

    services = list_community_services(db_session, ctx, q=unique_suffix, category=None)
    assert [row.name for row in services.items] == [f"Published service {unique_suffix}"]

    jobs = list_opportunities(db_session, ctx, kind="job", q=unique_suffix)
    assert [row.title for row in jobs] == [f"Published opening {unique_suffix}"]

    training = list_opportunities(db_session, ctx, kind="training", q=unique_suffix)
    assert [row.title for row in training] == [f"Published course {unique_suffix}"]

    with pytest.raises(HTTPException) as denied:
        list_opportunities(db_session, _ctx(HMoreRole.LANDLORD, org_a.id, user), kind="job", q=None)
    assert denied.value.status_code == 403


@pytest.mark.postgres
def test_tenant_document_upload_links_own_row(db_session, unique_suffix: str) -> None:
    from sqlalchemy import select

    from app.core.config import Settings
    from app.db.models import ManagedDocument, ManagedDocumentCategory, ManagedDocumentLink, Organisation, Tenant, User
    from app.storage.memory import InMemoryStorage

    org = Organisation(name="Org", slug=f"f41-doc-{unique_suffix}")
    user = User(
        email=f"doc-{unique_suffix}@example.com",
        display_name="Doc",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, user])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id,
        user_id=user.id,
        preferred_name="Doc",
        status=RecordStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.flush()
    created = upload_own_document(
        db_session,
        _ctx(HMoreRole.TENANT, org.id, user),
        title="My letter",
        filename="letter.pdf",
        content_type="application/pdf",
        data=b"%PDF-1.4 tenant",
        settings=Settings(storage_provider="memory", storage_max_upload_bytes=1_000_000),
        backend=InMemoryStorage(),
    )
    assert created["title"] == "My letter"
    assert created["access_classification"] == "standard"
    assert created["category_code"] == "tenant_submission"
    saved = db_session.scalar(
        select(ManagedDocumentLink).where(ManagedDocumentLink.document_id == created["id"])
    )
    assert saved is not None
    assert saved.link_type == "tenant"
    assert saved.link_id == tenant.id
    document = db_session.get(ManagedDocument, created["id"])
    assert document is not None
    category = db_session.get(ManagedDocumentCategory, document.category_id)
    assert category is not None
    assert category.code == "tenant_submission"
    assert category.title == "Tenant submissions"
    assert category.access_classification == "standard"

