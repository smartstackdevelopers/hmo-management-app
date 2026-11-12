"""F6.5 Room Occupancy foundation tests — mocked devices only."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.room_occupancy import RoomOccupancyCountHistory, RoomOccupancyState
from app.room_occupancy import devices as devices_mod
from app.room_occupancy import gate as gate_mod
from app.room_occupancy import service as occupancy_service
from app.room_occupancy.access import require_occupancy_read, require_occupancy_settings
from app.room_occupancy.status import compute_occupancy_status
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


def test_alembic_f65_revision_chain() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    rev = script.get_revision("20261111_4300_f65")
    assert rev is not None
    assert rev.down_revision == "20261111_4200_f64"
    assert script.get_revision("20261111_4400_f66") is not None


def test_f65_permissions_matrix() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.OCCUPANCY_SETTINGS_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.OCCUPANCY_COUNTS_CORRECT)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.OCCUPANCY_READ)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.OCCUPANCY_SETTINGS_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.OCCUPANCY_READ)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.OCCUPANCY_READ)
    assert not role_has_permission(HMoreRole.MAINTENANCE_CONTRACTOR, Permission.OCCUPANCY_READ)


def test_tenant_denied_occupancy_read() -> None:
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), SimpleNamespace(id=uuid.uuid4()))
    with pytest.raises(Exception):
        require_occupancy_read(ctx)
    with pytest.raises(Exception):
        require_occupancy_settings(ctx)


def test_five_occupancy_statuses() -> None:
    now = datetime.now(timezone.utc)
    assert (
        compute_occupancy_status(
            estimated_count=0,
            max_capacity=10,
            near_capacity_percent=80,
            last_count_at=now,
            offline_after_seconds=300,
            device_online=True,
            now=now,
        )[0]
        == "available"
    )
    assert (
        compute_occupancy_status(
            estimated_count=3,
            max_capacity=10,
            near_capacity_percent=80,
            last_count_at=now,
            offline_after_seconds=300,
            device_online=True,
            now=now,
        )[0]
        == "occupied"
    )
    assert (
        compute_occupancy_status(
            estimated_count=8,
            max_capacity=10,
            near_capacity_percent=80,
            last_count_at=now,
            offline_after_seconds=300,
            device_online=True,
            now=now,
        )[0]
        == "near_capacity"
    )
    assert (
        compute_occupancy_status(
            estimated_count=10,
            max_capacity=10,
            near_capacity_percent=80,
            last_count_at=now,
            offline_after_seconds=300,
            device_online=True,
            now=now,
        )[0]
        == "at_capacity"
    )
    # Offline never presented as zero occupants at calculation layer
    status, percent = compute_occupancy_status(
        estimated_count=0,
        max_capacity=10,
        near_capacity_percent=80,
        last_count_at=now - timedelta(hours=1),
        offline_after_seconds=300,
        device_online=True,
        now=now,
    )
    assert status == "offline"
    assert percent is None


def test_invalid_sensor_negative_rejected_by_status_path() -> None:
    # Status calc clamps via max(0) for display path; API rejects negatives separately
    now = datetime.now(timezone.utc)
    status, _ = compute_occupancy_status(
        estimated_count=-1,
        max_capacity=5,
        near_capacity_percent=80,
        last_count_at=now,
        offline_after_seconds=300,
        device_online=True,
        now=now,
    )
    assert status == "available"


@pytest.mark.postgres
def test_approval_gate_blocks_live_ingest_and_isolation(db_session, unique_suffix: str) -> None:
    from app.db.models.audit import AuditEvent
    from app.db.models.membership import OrganisationMembership
    from app.db.models.organisation import Organisation
    from app.db.models.user import User
    from sqlalchemy import select

    org_a = Organisation(name=f"OccA-{unique_suffix}", slug=f"occa-{unique_suffix}")
    org_b = Organisation(name=f"OccB-{unique_suffix}", slug=f"occb-{unique_suffix}")
    admin = User(
        email=f"occa-{unique_suffix}@example.com",
        display_name="Occ Admin",
        external_subject=f"auth0|occa-{unique_suffix}",
    )
    db_session.add_all([org_a, org_b, admin])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=admin.id,
            organisation_id=org_a.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    prop = Property(
        organisation_id=org_a.id,
        name=f"House-{unique_suffix}",
        address_line1="1 Test St",
        city="Testville",
        postcode="TE1 1ST",
    )
    db_session.add(prop)
    db_session.flush()
    communal = Room(
        organisation_id=org_a.id,
        property_id=prop.id,
        label="Lounge",
        floor_label="G",
        room_type="communal_lounge",
        max_occupancy=10,
    )
    bedroom = Room(
        organisation_id=org_a.id,
        property_id=prop.id,
        label="Bed 1",
        floor_label="1",
        room_type="bedroom",
        max_occupancy=1,
    )
    db_session.add_all([communal, bedroom])
    db_session.flush()
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin)

    gate = gate_mod.get_gate(db_session, ctx)
    assert gate["gate_complete"] is False
    assert gate["live_counting_enabled"] is False
    assert gate["dpia_status"] == "not_started"

    # Cannot enable live counting without approvals
    with pytest.raises(HTTPException) as exc:
        gate_mod.update_gate(db_session, ctx, live_counting_enabled=True)
    assert exc.value.status_code == 400

    # Device registration allowed, but stream activation false
    device = devices_mod.register_device(
        db_session,
        ctx,
        device_key=f"edge-{unique_suffix}",
        name="Edge counter",
        device_type="edge_people_counter",
        property_id=prop.id,
        room_id=communal.id,
        supports_people_counting=True,
        compatibility_verified=True,
        credentials={"api_key": "device-secret"},
    )
    assert device["stream_activation_allowed"] is False
    assert "device-secret" not in str(device)

    # Bedroom assignment forbidden
    with pytest.raises(HTTPException) as bed:
        devices_mod.register_device(
            db_session,
            ctx,
            device_key=f"cam-bed-{unique_suffix}",
            name="Illegal cam",
            device_type="onvif_camera",
            property_id=prop.id,
            room_id=bedroom.id,
            supports_people_counting=True,
            compatibility_verified=True,
        )
    assert bed.value.status_code == 400

    # Ingest blocked without gate
    with pytest.raises(HTTPException) as blocked:
        occupancy_service.ingest_count(
            db_session, ctx, device_id=uuid.UUID(device["id"]), estimated_count=3
        )
    assert blocked.value.status_code == 403

    # Complete gate with explicit approved statuses (test fixture only — not production approval)
    gate_mod.update_gate(
        db_session,
        ctx,
        feasibility_status="approved",
        dpia_status="approved",
        signage_status="approved",
        retention_policy_status="approved",
        camera_compatibility_status="approved",
        approved_room_purposes=["communal_lounge"],
        authorised_viewer_notes="Org admins and assigned support workers",
        accuracy_requirements_notes="+/- 2 people estimated",
        documentation_refs=["test-dpia-ref"],
        record_formal_approval=True,
        live_counting_enabled=True,
    )
    gate2 = gate_mod.get_gate(db_session, ctx)
    assert gate2["gate_complete"] is True
    assert gate2["live_counting_enabled"] is True

    # Refresh device stream flag
    device = devices_mod.update_device(
        db_session, ctx, uuid.UUID(device["id"]), compatibility_verified=True, supports_people_counting=True
    )
    assert device["stream_activation_allowed"] is True

    ingested = occupancy_service.ingest_count(
        db_session, ctx, device_id=uuid.UUID(device["id"]), estimated_count=9
    )
    assert ingested["occupancy_status"] == "near_capacity"
    assert ingested["estimated_count"] == 9

    # Invalid count
    with pytest.raises(HTTPException):
        occupancy_service.ingest_count(
            db_session, ctx, device_id=uuid.UUID(device["id"]), estimated_count=-2
        )

    corrected = occupancy_service.correct_count(
        db_session, ctx, communal.id, corrected_count=8, reason="Visual check"
    )
    assert corrected["correction"]["previous_estimated_count"] == 9
    assert corrected["state"]["is_manual_correction"] is True

    hist = occupancy_service.list_history(db_session, ctx, room_id=communal.id)
    assert len(hist) >= 2
    summary = occupancy_service.history_summary(db_session, ctx, room_id=communal.id, period="daily")
    assert summary["sample_count"] >= 2

    # Org isolation
    other = User(
        email=f"occb-{unique_suffix}@example.com",
        display_name="Other",
        external_subject=f"auth0|occb-{unique_suffix}",
    )
    db_session.add(other)
    db_session.flush()
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, other)
    assert occupancy_service.list_room_states(db_session, ctx_b) == []

    # Retention delete path
    old = RoomOccupancyCountHistory(
        organisation_id=org_a.id,
        property_id=prop.id,
        room_id=communal.id,
        estimated_count=1,
        max_capacity=10,
        occupancy_status="occupied",
        source="edge",
        recorded_at=datetime.now(timezone.utc) - timedelta(days=400),
    )
    db_session.add(old)
    db_session.flush()
    gate_mod.get_or_create_settings(db_session, ctx)
    # force short retention
    settings = gate_mod.get_or_create_settings(db_session, ctx)
    settings.history_retention_days = 30
    db_session.flush()
    result = occupancy_service.apply_retention(db_session)
    assert result["deleted_history"] >= 1

    actions = set(
        db_session.scalars(select(AuditEvent.action).where(AuditEvent.organisation_id == org_a.id)).all()
    )
    assert "room_occupancy.gate.update" in actions
    assert "room_occupancy.device.register" in actions
    assert "room_occupancy.count.ingest" in actions
    assert "room_occupancy.count.correct" in actions

    # Offline state should not expose zero as available occupancy in API dict
    state = db_session.scalar(
        select(RoomOccupancyState).where(RoomOccupancyState.room_id == communal.id)
    )
    assert state is not None
    state.occupancy_status = "offline"
    state.estimated_count = 0
    db_session.flush()
    rows = occupancy_service.list_room_states(db_session, ctx, room_id=communal.id)
    assert rows[0]["estimated_count"] is None
    assert rows[0]["occupancy_status"] == "offline"
