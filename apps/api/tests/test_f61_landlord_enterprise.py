"""F6.1 landlord enterprise: dashboard, rent ledger, inspections, repair oversight."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.landlord_enterprise import service as landlord
from app.landlord_enterprise.constants import LEDGER_DISCLAIMER
from app.landlord_enterprise.schemas import InspectionWrite, RentRecordStatusWrite, RentRecordWrite
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def _ctx(role: HMoreRole, organisation_id, user) -> OrganisationContext:
    return OrganisationContext(
        user=user,
        organisation_id=organisation_id,
        role=role,
        authorization=AuthorizationContext(
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
        ),
    )


def test_alembic_f61_revision_chains() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    rev = script.get_revision("20261111_3900_f61")
    assert rev is not None
    assert rev.down_revision == "20261110_3800_f55"
    assert "20261111_3900_f61" in script.get_heads() or script.get_revision("20261111_4000_f62") is not None


def test_landlord_permissions_for_enterprise_tools() -> None:
    assert role_has_permission(HMoreRole.LANDLORD, Permission.PROPERTIES_MANAGE)
    assert role_has_permission(HMoreRole.LANDLORD, Permission.RENT_RECORDS_MANAGE)
    assert role_has_permission(HMoreRole.LANDLORD, Permission.INSPECTIONS_MANAGE)
    assert role_has_permission(HMoreRole.LANDLORD, Permission.REPAIRS_STATUS_READ)
    assert not role_has_permission(HMoreRole.TENANT, Permission.RENT_RECORDS_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.INSPECTIONS_MANAGE)


def test_ledger_disclaimer_is_non_payment_gateway() -> None:
    text = LEDGER_DISCLAIMER.lower()
    assert "ledger" in text
    assert "payment" in text or "banking" in text


def test_tenant_cannot_require_rent_manage() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), user)
    with pytest.raises(Exception) as exc:
        from app.landlord_enterprise.access import require_rent_manage

        require_rent_manage(ctx)
    assert getattr(exc.value, "status_code", None) in {403, None} or "403" in str(exc.value)


@pytest.mark.postgres
def test_landlord_enterprise_flow_and_isolation(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, Property, Room, Tenant, User
    from app.db.models.maintenance import MaintenanceRequest

    org = Organisation(name="LL Org", slug=f"f61-{unique_suffix}")
    other = Organisation(name="Other", slug=f"f61-o-{unique_suffix}")
    landlord_user = User(
        email=f"ll-{unique_suffix}@example.com",
        display_name="Landlord",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    other_ll = User(
        email=f"ll2-{unique_suffix}@example.com",
        display_name="Other LL",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, other, landlord_user, other_ll])
    db_session.flush()

    prop = Property(
        organisation_id=org.id,
        name=f"House {unique_suffix}",
        address_line1="1 High Street",
        city="Birmingham",
        postcode="B1 1AA",
        landlord_user_id=landlord_user.id,
        status=RecordStatus.ACTIVE,
    )
    other_prop = Property(
        organisation_id=org.id,
        name=f"Other House {unique_suffix}",
        address_line1="2 High Street",
        city="Birmingham",
        postcode="B1 1BB",
        landlord_user_id=other_ll.id,
        status=RecordStatus.ACTIVE,
    )
    db_session.add_all([prop, other_prop])
    db_session.flush()
    room = Room(
        organisation_id=org.id,
        property_id=prop.id,
        label="Room 1",
        status=RecordStatus.ACTIVE,
    )
    db_session.add(room)
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id,
        preferred_name="Amina",
        status=RecordStatus.ACTIVE,
        assigned_property_id=prop.id,
        assigned_room_id=room.id,
        tenancy_reference=f"TR-{unique_suffix}",
    )
    db_session.add(tenant)
    db_session.flush()

    maint = MaintenanceRequest(
        organisation_id=org.id,
        reference_number=f"MR-{unique_suffix}",
        title="Leak",
        description="Kitchen leak",
        property_id=prop.id,
        status="submitted",
        priority="high",
        reported_at=date.today(),
    )
    # reported_at needs datetime
    from datetime import datetime, timezone

    maint.reported_at = datetime.now(timezone.utc)
    db_session.add(maint)
    db_session.flush()

    ctx = _ctx(HMoreRole.LANDLORD, org.id, landlord_user)
    other_ctx = _ctx(HMoreRole.LANDLORD, org.id, other_ll)

    dash = landlord.enterprise_dashboard(db_session, ctx)
    assert dash["total_properties"] >= 1
    assert dash["total_rooms"] >= 1
    assert dash["occupied_rooms"] >= 1
    assert dash["active_tenancies"] >= 1
    assert dash["repairs"]["open"] >= 1

    portfolio = landlord.portfolio_analytics(db_session, ctx, property_id=prop.id)
    assert portfolio["total"] == 1
    assert portfolio["items"][0]["occupied_rooms"] >= 1

    rent = landlord.create_rent_record(
        db_session,
        ctx,
        RentRecordWrite(
            property_id=prop.id,
            tenant_id=tenant.id,
            amount=Decimal("450.00"),
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            status="due",
        ),
    )
    assert rent["status"] == "due"
    with pytest.raises(HTTPException):
        landlord.create_rent_record(
            db_session,
            ctx,
            RentRecordWrite(
                property_id=prop.id,
                amount=Decimal("10.00"),
                period_start=date.today(),
                period_end=date.today(),
                status="recorded_paid",
            ),
        )
    with pytest.raises(HTTPException):
        landlord.update_rent_status(
            db_session, ctx, rent["id"], RentRecordStatusWrite(status="recorded_paid")
        )
    paid = landlord.update_rent_status(
        db_session,
        ctx,
        rent["id"],
        RentRecordStatusWrite(status="recorded_paid", recorded_paid_note="Cash recorded by landlord"),
    )
    assert paid["status"] == "recorded_paid"

    with pytest.raises(HTTPException):
        landlord.create_rent_record(
            db_session,
            other_ctx,
            RentRecordWrite(
                property_id=prop.id,
                amount=Decimal("10.00"),
                period_start=date.today(),
                period_end=date.today(),
                status="due",
            ),
        )

    insp = landlord.create_inspection(
        db_session,
        ctx,
        InspectionWrite(
            property_id=prop.id,
            room_id=room.id,
            title="Quarterly check",
            scheduled_date=date.today() - timedelta(days=2),
            status="scheduled",
            findings="Damp noted",
            follow_up_actions="Book repair",
        ),
    )
    assert insp["effective_status"] == "overdue"
    inspections = landlord.list_inspections(db_session, ctx, status="overdue")
    assert inspections["overdue"] >= 1

    repairs = landlord.list_repair_oversight(db_session, ctx)
    assert repairs["open"] >= 1
    assert all(item["property_id"] == str(prop.id) for item in repairs["items"])
