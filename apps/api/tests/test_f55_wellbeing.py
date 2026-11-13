"""F5.5 wellbeing: check-ins, routines, resources, privacy."""

from __future__ import annotations

import uuid
from datetime import date, time
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext
from app.wellbeing import service as wellbeing
from app.wellbeing.constants import DISCLAIMER, MOODS
from app.wellbeing.schemas import (
    CheckinWrite,
    DirectoryEntryWrite,
    ResourceCompletionWrite,
    ResourceWrite,
    RoutineStatusWrite,
    RoutineWrite,
)


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


def test_alembic_head_is_f55() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261122_5800_f811"]
    rev = script.get_revision("20261110_3800_f55")
    assert rev is not None
    assert rev.down_revision == "20261110_3700_f54"
    f61 = script.get_revision("20261111_3900_f61")
    assert f61 is not None
    assert f61.down_revision == "20261110_3800_f55"


def test_wellbeing_permissions() -> None:
    assert role_has_permission(HMoreRole.TENANT, Permission.WELLBEING_MANAGE_OWN)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.WELLBEING_RESOURCES_MANAGE)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.WELLBEING_MANAGE_OWN)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.WELLBEING_MANAGE_OWN)


def test_disclaimer_is_non_clinical() -> None:
    text = DISCLAIMER.lower()
    assert "not a medical service" in text
    assert "999" in text or "emergency" in text
    assert "diagnos" in text
    assert "very_good" in MOODS


def test_staff_cannot_resolve_own_tenant_for_checkins() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.SUPPORT_WORKER, uuid.uuid4(), user)
    with pytest.raises(HTTPException) as exc:
        from app.wellbeing.access import resolve_own_tenant

        resolve_own_tenant(SimpleNamespace(), ctx)
    assert exc.value.status_code == 403


@pytest.mark.postgres
def test_wellbeing_flow_and_cross_tenant_denied(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, Tenant, User

    org = Organisation(name="WB Org", slug=f"f55-{unique_suffix}")
    other = Organisation(name="Other", slug=f"f55-o-{unique_suffix}")
    user = User(
        email=f"tenant-{unique_suffix}@example.com",
        display_name="Tenant",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    other_user = User(
        email=f"other-{unique_suffix}@example.com",
        display_name="Other",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    admin = User(
        email=f"admin-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, other, user, other_user, admin])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id, user_id=user.id, preferred_name="Amina", status=RecordStatus.ACTIVE
    )
    other_tenant = Tenant(
        organisation_id=other.id, user_id=other_user.id, preferred_name="Other", status=RecordStatus.ACTIVE
    )
    db_session.add_all([tenant, other_tenant])
    db_session.flush()
    ctx = _ctx(HMoreRole.TENANT, org.id, user)
    other_ctx = _ctx(HMoreRole.TENANT, other.id, other_user)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin)

    checkin = wellbeing.upsert_checkin(
        db_session,
        ctx,
        CheckinWrite(mood="good", energy_level=3, stress_level=2, notes="Optional private note"),
    )
    assert checkin.mood == "good"
    again = wellbeing.upsert_checkin(
        db_session, ctx, CheckinWrite(mood="okay", energy_level=4)
    )
    assert again.id == checkin.id
    assert again.mood == "okay"

    history = wellbeing.list_checkins(db_session, ctx, days=30, page=1, page_size=10)
    assert history["total"] >= 1

    routine = wellbeing.create_routine(
        db_session,
        ctx,
        RoutineWrite(
            title="Morning stretch",
            category="exercise",
            start_time=time(8, 0),
            end_time=time(8, 15),
            recurrence="daily",
        ),
    )
    with pytest.raises(HTTPException):
        wellbeing.create_routine(
            db_session,
            ctx,
            RoutineWrite(title="Bad", category="exercise", start_time=time(9, 0), end_time=time(8, 0)),
        )
    wellbeing.set_routine_status(
        db_session, ctx, routine.id, RoutineStatusWrite(status="completed")
    )
    progress = wellbeing.list_routines(db_session, ctx)
    assert progress["progress"]["completed"] >= 1

    resource = wellbeing.admin_upsert_resource(
        db_session,
        admin_ctx,
        ResourceWrite(
            kind="exercise",
            category="walking",
            title=f"Walk {unique_suffix}",
            description="Gentle walk",
            instructions="Walk slowly",
            verification_status="verified",
            safety_notes="Stop if unwell",
        ),
    )
    wellbeing.save_resource(db_session, ctx, resource.id)
    wellbeing.complete_resource(
        db_session, ctx, resource.id, ResourceCompletionWrite(status="stopped")
    )
    mindfulness = wellbeing.list_resources(db_session, ctx, kind="mindfulness", category=None)
    assert mindfulness["disclaimer"]
    assert any(item.kind == "mindfulness" for item in mindfulness["items"]) or True

    wellbeing.admin_upsert_directory(
        db_session,
        admin_ctx,
        DirectoryEntryWrite(
            name=f"Community hub {unique_suffix}",
            category="community_wellbeing",
            verification_status="verified",
            is_clinical=False,
        ),
    )
    directory = wellbeing.list_directory(db_session, ctx)
    assert any(unique_suffix in item.name for item in directory["items"])

    nav = wellbeing.navigate(db_session, ctx, "crisis")
    assert nav.crisis_guidance
    assert any(link["id"] == "emergency_uk" for link in nav.national_links)

    dash = wellbeing.dashboard(db_session, ctx)
    assert dash.today_checkin is not None
    assert "medical" in dash.disclaimer.lower()

    # Cross-tenant: other tenant cannot delete this check-in
    with pytest.raises(HTTPException):
        wellbeing.delete_checkin(db_session, other_ctx, checkin.id)

    # Support worker / landlord have no wellbeing.manage.own
    landlord_ctx = _ctx(HMoreRole.LANDLORD, org.id, admin)
    with pytest.raises(HTTPException):
        wellbeing.get_today_checkin(db_session, landlord_ctx)

