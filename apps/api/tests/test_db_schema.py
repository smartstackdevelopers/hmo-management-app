"""PostgreSQL schema and migration tests for F1.2."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.models import (
    AuditEvent,
    EmergencyAccess,
    FileMetadata,
    HMoreRole,
    Organisation,
    OrganisationMembership,
    Property,
    Room,
    Tenant,
    User,
)


pytestmark = pytest.mark.postgres


def test_database_connection(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1


def test_pgvector_extension_installed(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        installed = connection.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one_or_none()
    assert installed == "vector"


def test_expected_tables_exist(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    tables = set(inspector.get_table_names())
    expected = {
        "organisations",
        "users",
        "organisation_memberships",
        "tenants",
        "properties",
        "rooms",
        "audit_events",
        "emergency_access_grants",
        "file_metadata",
        "case_assignments",
        "daily_logs",
        "handovers",
        "staff_shifts",
        "tenant_visits",
        "operational_tasks",
        "reminder_records",
        "staff_training_records",
        "safeguarding_reminders",
        "incidents",
        "incident_status_history",
        "incident_follow_ups",
        "housing_applications",
        "housing_application_status_history",
        "housing_application_decisions",
        "waiting_list_entries",
        "alembic_version",
    }
    assert expected.issubset(tables)


def test_users_authorization_version_column(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    columns = {column["name"] for column in inspector.get_columns("users")}
    assert "authorization_version" in columns


def test_migration_history_has_single_head(alembic_config) -> None:
    script = ScriptDirectory.from_config(alembic_config)
    heads = script.get_heads()
    assert heads == ["20261107_1800_f36"]


def test_upgrade_downgrade_roundtrip(alembic_config, migrated_engine: Engine) -> None:
    # Fixture already upgraded to head. Prove downgrade and re-upgrade work.
    command.downgrade(alembic_config, "base")
    inspector = inspect(migrated_engine)
    assert "organisations" not in inspector.get_table_names()
    command.upgrade(alembic_config, "head")
    inspector = inspect(migrated_engine)
    assert "organisations" in inspector.get_table_names()


def test_organisation_and_user_unique_constraints(
    db_session: Session, unique_suffix: str
) -> None:
    org = Organisation(id=uuid4(), name="Riverside", slug=f"riverside-{unique_suffix}")
    user = User(
        id=uuid4(),
        email=f"admin-{unique_suffix}@example.com",
        display_name="Org Admin",
    )
    db_session.add_all([org, user])
    db_session.flush()

    db_session.add(
        Organisation(
            id=uuid4(),
            name="Other",
            slug=f"riverside-{unique_suffix}",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_non_super_admin_membership_requires_organisation(
    db_session: Session, unique_suffix: str
) -> None:
    org = Organisation(id=uuid4(), name="Org", slug=f"org-{unique_suffix}")
    user = User(
        id=uuid4(),
        email=f"worker-{unique_suffix}@example.com",
        display_name="Worker",
    )
    db_session.add_all([org, user])
    db_session.flush()

    db_session.add(
        OrganisationMembership(
            id=uuid4(),
            user_id=user.id,
            organisation_id=None,
            role=HMoreRole.SUPPORT_WORKER,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_super_admin_membership_allows_null_organisation(
    db_session: Session, unique_suffix: str
) -> None:
    user = User(
        id=uuid4(),
        email=f"super-{unique_suffix}@example.com",
        display_name="Super Admin",
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            id=uuid4(),
            user_id=user.id,
            organisation_id=None,
            role=HMoreRole.SUPER_ADMIN,
        )
    )
    db_session.flush()
    loaded = db_session.scalar(
        select(OrganisationMembership).where(OrganisationMembership.user_id == user.id)
    )
    assert loaded is not None
    assert loaded.role == HMoreRole.SUPER_ADMIN
    assert loaded.organisation_id is None


def test_foreign_keys_and_relationships(db_session: Session, unique_suffix: str) -> None:
    org = Organisation(id=uuid4(), name="Housing Co", slug=f"housing-{unique_suffix}")
    landlord = User(
        id=uuid4(),
        email=f"landlord-{unique_suffix}@example.com",
        display_name="Landlord",
    )
    db_session.add_all([org, landlord])
    db_session.flush()

    membership = OrganisationMembership(
        id=uuid4(),
        user_id=landlord.id,
        organisation_id=org.id,
        role=HMoreRole.LANDLORD,
    )
    tenant = Tenant(
        id=uuid4(),
        organisation_id=org.id,
        preferred_name="Ali Hassan",
        email=f"ali-{unique_suffix}@example.com",
    )
    prop = Property(
        id=uuid4(),
        organisation_id=org.id,
        name="Elm Road House",
        address_line1="14 Elm Road",
        city="Birmingham",
        postcode="B1 1AA",
        landlord_user_id=landlord.id,
    )
    db_session.add_all([membership, tenant, prop])
    db_session.flush()

    room = Room(
        id=uuid4(),
        organisation_id=org.id,
        property_id=prop.id,
        label="14",
        max_occupancy=1,
    )
    audit = AuditEvent(
        id=uuid4(),
        organisation_id=org.id,
        actor_user_id=landlord.id,
        action="property.create",
        resource_type="property",
        resource_id=str(prop.id),
        metadata_json={"source": "test"},
    )
    grant = EmergencyAccess(
        id=uuid4(),
        organisation_id=org.id,
        actor_user_id=landlord.id,
        reason="Safeguarding review",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    file_row = FileMetadata(
        id=uuid4(),
        organisation_id=org.id,
        storage_key=f"org/{org.id}/docs/{unique_suffix}.pdf",
        original_filename="consent.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        uploaded_by_user_id=landlord.id,
        resource_type="tenant",
        resource_id=str(tenant.id),
    )
    db_session.add_all([room, audit, grant, file_row])
    db_session.flush()

    loaded = db_session.scalar(select(Property).where(Property.id == prop.id))
    assert loaded is not None
    assert loaded.organisation_id == org.id
    assert len(loaded.rooms) == 1
    assert loaded.rooms[0].label == "14"


def test_room_label_unique_per_property(db_session: Session, unique_suffix: str) -> None:
    org = Organisation(id=uuid4(), name="Dup", slug=f"dup-{unique_suffix}")
    prop = Property(
        id=uuid4(),
        organisation_id=org.id,
        name="House",
        address_line1="1 High Street",
        city="Leeds",
        postcode="LS1 1AA",
    )
    db_session.add_all([org, prop])
    db_session.flush()

    db_session.add(
        Room(
            id=uuid4(),
            organisation_id=org.id,
            property_id=prop.id,
            label="A",
        )
    )
    db_session.flush()
    db_session.add(
        Room(
            id=uuid4(),
            organisation_id=org.id,
            property_id=prop.id,
            label="A",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_required_fields_reject_null_name(db_session: Session, unique_suffix: str) -> None:
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO organisations (id, name, slug) VALUES (:id, NULL, :slug)"
            ),
            {"id": str(uuid4()), "slug": f"bad-{unique_suffix}"},
        )
        db_session.flush()
