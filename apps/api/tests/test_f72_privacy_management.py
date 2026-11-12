"""F7.2 privacy management tests."""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.db.models.enums import HMoreRole, MembershipStatus
from app.privacy import access as privacy_access
from app.privacy.catalog import DEFAULT_DPIA_ACTIVITIES, INVENTORY_CATALOG
from app.privacy.constants import DPIA_STATUSES
from app.privacy import service as privacy_service
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def _ctx(role: HMoreRole, organisation_id: uuid.UUID) -> OrganisationContext:
    user = SimpleNamespace(id=uuid.uuid4())
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
    return OrganisationContext(user=user, organisation_id=organisation_id, role=role, authorization=authz)


def test_alembic_f72_revision_chain() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    rev = script.get_revision("20261112_4600_f72")
    assert rev is not None
    assert rev.down_revision == "20261111_4500_f67"


def test_f72_permissions_matrix() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.PRIVACY_MANAGE)
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.PRIVACY_READ)
    assert not role_has_permission(HMoreRole.TENANT, Permission.PRIVACY_READ)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.PRIVACY_MANAGE)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.PRIVACY_MANAGE)


def test_tenant_denied_privacy_read() -> None:
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        privacy_access.require_privacy_read(ctx)
    assert exc.value.status_code == 403


def test_catalog_does_not_invent_retention_days() -> None:
    for item in INVENTORY_CATALOG:
        assert item.get("retention_period_days") is None


def test_default_dpia_never_starts_approved() -> None:
    for item in DEFAULT_DPIA_ACTIVITIES:
        assert item.get("status") != "approved"
        assert item["activity_key"] != ""


def test_dpia_status_enum_includes_pending_approval() -> None:
    assert "pending_approval" in DPIA_STATUSES
    assert "approved" in DPIA_STATUSES


@pytest.mark.postgres
def test_bootstrap_and_dpia_approval_requires_fields(db_session, unique_suffix: str) -> None:
    from app.db.models.membership import OrganisationMembership
    from app.db.models.organisation import Organisation
    from app.db.models.user import User

    org = Organisation(name=f"Priv-{unique_suffix}", slug=f"priv-{unique_suffix}")
    admin = User(
        email=f"priv-{unique_suffix}@example.com",
        display_name="Privacy Admin",
        external_subject=f"auth0|priv-{unique_suffix}",
    )
    db_session.add_all([org, admin])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=admin.id,
            organisation_id=org.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    ctx = OrganisationContext(
        user=admin,
        organisation_id=org.id,
        role=HMoreRole.ORGANISATION_ADMIN,
        authorization=_ctx(HMoreRole.ORGANISATION_ADMIN, org.id).authorization,
    )
    result = privacy_service.bootstrap_catalog(db_session, ctx)
    assert result["created_inventory"] == len(INVENTORY_CATALOG)
    assert result["created_dpia"] == len(DEFAULT_DPIA_ACTIVITIES)

    entries = privacy_service.list_dpia(db_session, ctx)
    occ = next(e for e in entries if e["activity_key"] == "room_occupancy_live")
    assert occ["status"] in ("not_started", "pending_approval")

    entry_id = uuid.UUID(occ["id"])
    with pytest.raises(HTTPException) as exc:
        privacy_service.update_dpia(db_session, ctx, entry_id, {"status": "approved"})
    assert exc.value.status_code == 400

    updated = privacy_service.update_dpia(
        db_session,
        ctx,
        entry_id,
        {
            "status": "approved",
            "approval_reference": "DPIA-EXAMPLE-001",
            "approved_by_name": "Data Protection Lead (authorised)",
        },
    )
    assert updated["status"] == "approved"
    assert updated["approval_reference"] == "DPIA-EXAMPLE-001"


@pytest.mark.postgres
def test_dsr_erasure_requires_evidence(db_session, unique_suffix: str) -> None:
    from app.db.models.organisation import Organisation
    from app.db.models.user import User

    org = Organisation(name=f"DSR-{unique_suffix}", slug=f"dsr-{unique_suffix}")
    admin = User(
        email=f"dsr-{unique_suffix}@example.com",
        display_name="DSR Admin",
        external_subject=f"auth0|dsr-{unique_suffix}",
    )
    db_session.add_all([org, admin])
    db_session.flush()
    ctx = OrganisationContext(
        user=admin,
        organisation_id=org.id,
        role=HMoreRole.ORGANISATION_ADMIN,
        authorization=_ctx(HMoreRole.ORGANISATION_ADMIN, org.id).authorization,
    )
    dsr = privacy_service.create_dsr(
        db_session,
        ctx,
        {"request_category": "erasure", "subject_label": "Test Data Subject"},
    )
    with pytest.raises(HTTPException) as exc:
        privacy_service.update_dsr(db_session, ctx, uuid.UUID(dsr["id"]), {"status": "completed"})
    assert exc.value.status_code == 400


@pytest.mark.postgres
def test_test_retention_purge_only_test_rows(db_session, unique_suffix: str) -> None:
    from app.db.models.organisation import Organisation
    from app.db.models.user import User

    org = Organisation(name=f"Purge-{unique_suffix}", slug=f"purge-{unique_suffix}")
    admin = User(
        email=f"purge-{unique_suffix}@example.com",
        display_name="Purge Admin",
        external_subject=f"auth0|purge-{unique_suffix}",
    )
    db_session.add_all([org, admin])
    db_session.flush()
    ctx = OrganisationContext(
        user=admin,
        organisation_id=org.id,
        role=HMoreRole.ORGANISATION_ADMIN,
        authorization=_ctx(HMoreRole.ORGANISATION_ADMIN, org.id).authorization,
    )
    privacy_service.create_test_retention_record(db_session, ctx, "purge-me", expire_days=-1)
    result = privacy_service.run_test_retention_purge(db_session, ctx)
    assert result["records_deleted"] >= 1
