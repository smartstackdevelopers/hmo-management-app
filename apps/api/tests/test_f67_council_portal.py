"""F6.7 Council Portal — add-on outside core six HMoreRole values."""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.council_portal import service as portal_service
from app.council_portal.access import require_council_portal_manage
from app.council_portal.constants import PORTAL_DISCLAIMER
from app.council_portal.context import CouncilPortalContext
from app.db.models.enums import HMoreRole, MembershipStatus
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.rbac.roles import APPROVED_ROLE_COUNT
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


def test_alembic_head_is_f67() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261120_5600_f88"]
    rev = script.get_revision("20261111_4500_f67")
    assert rev is not None
    assert rev.down_revision == "20261111_4400_f66"


def test_core_still_exactly_six_roles() -> None:
    assert len(HMoreRole) == APPROVED_ROLE_COUNT == 6
    assert "council_officer" not in {r.value for r in HMoreRole}


def test_f67_manage_permission_matrix() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.COUNCIL_PORTAL_MANAGE)
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.COUNCIL_PORTAL_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.COUNCIL_PORTAL_MANAGE)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.COUNCIL_PORTAL_MANAGE)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.COUNCIL_PORTAL_MANAGE)


def test_tenant_cannot_manage_council_portal() -> None:
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), SimpleNamespace(id=uuid.uuid4()))
    with pytest.raises(Exception):
        require_council_portal_manage(ctx)


def test_disclaimer_isolates_addon_role() -> None:
    assert "add-on" in PORTAL_DISCLAIMER.lower() or "optional" in PORTAL_DISCLAIMER.lower()
    assert "core" in PORTAL_DISCLAIMER.lower()


@pytest.mark.postgres
def test_council_share_officer_view_and_isolation(db_session, unique_suffix: str) -> None:
    from sqlalchemy import select

    from app.db.models.audit import AuditEvent
    from app.db.models.housing import HousingApplication
    from app.db.models.membership import OrganisationMembership
    from app.db.models.organisation import Organisation
    from app.db.models.tenant import Tenant
    from app.db.models.user import User

    org_a = Organisation(name=f"CounA-{unique_suffix}", slug=f"couna-{unique_suffix}")
    org_b = Organisation(name=f"CounB-{unique_suffix}", slug=f"counb-{unique_suffix}")
    admin = User(
        email=f"couna-{unique_suffix}@example.com",
        display_name="Org Admin",
        external_subject=f"auth0|couna-{unique_suffix}",
    )
    officer_user = User(
        email=f"officer-{unique_suffix}@example.com",
        display_name="Council Officer",
        external_subject=f"auth0|officer-{unique_suffix}",
    )
    db_session.add_all([org_a, org_b, admin, officer_user])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=admin.id,
            organisation_id=org_a.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    # Officer intentionally has NO organisation_memberships row for org_a
    tenant = Tenant(
        organisation_id=org_a.id,
        preferred_name=f"Tenant {unique_suffix}",
        full_name=f"Tenant {unique_suffix}",
        tenancy_reference=f"T-{unique_suffix}",
    )
    db_session.add(tenant)
    db_session.flush()
    app = HousingApplication(
        organisation_id=org_a.id,
        reference_number=f"APP-{unique_suffix}",
        tenant_id=tenant.id,
        housing_requirements="One bedroom supported",
        priority="normal",
        status="under_review",
    )
    db_session.add(app)
    db_session.flush()
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin)

    invited = portal_service.invite_officer(
        db_session, ctx, user_id=officer_user.id, council_organisation_name="Test Council"
    )
    assert invited["addon_role_label"] == "council_officer"
    assert invited["status"] == "active"

    share = portal_service.create_share(
        db_session,
        ctx,
        application_id=app.id,
        purpose="Nomination review",
        include_approval_history=True,
        include_evidence=False,
        scopes=["application_status", "approval_history"],
    )
    assert share["status"] == "active"

    cctx = CouncilPortalContext(
        user=officer_user,
        organisation_id=org_a.id,
        officer_id=uuid.UUID(invited["id"]),
    )
    inbox = portal_service.officer_inbox(db_session, cctx)
    assert len(inbox["items"]) == 1
    assert inbox["items"][0]["tenant_records_exposed"] is False
    assert "tenant_id" not in inbox["items"][0]

    detail = portal_service.officer_get_application(db_session, cctx, uuid.UUID(share["id"]))
    assert detail["reference_number"] == app.reference_number
    assert detail["tenant_records_exposed"] is False

    report = portal_service.officer_report_summary(db_session, cctx)
    assert report["shared_application_count"] == 1

    # Org B admin cannot see org A shares
    other_admin = User(
        email=f"counb-{unique_suffix}@example.com",
        display_name="Other Admin",
        external_subject=f"auth0|counb-{unique_suffix}",
    )
    db_session.add(other_admin)
    db_session.flush()
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, other_admin)
    assert portal_service.list_shares(db_session, ctx_b) == []

    # Draft cannot be shared
    draft = HousingApplication(
        organisation_id=org_a.id,
        reference_number=f"APP-D-{unique_suffix}",
        tenant_id=tenant.id,
        housing_requirements="Draft",
        priority="normal",
        status="draft",
    )
    db_session.add(draft)
    db_session.flush()
    with pytest.raises(HTTPException):
        portal_service.create_share(
            db_session, ctx, application_id=draft.id, purpose="Should fail"
        )

    portal_service.revoke_share(db_session, ctx, uuid.UUID(share["id"]))
    with pytest.raises(HTTPException):
        portal_service.officer_get_application(db_session, cctx, uuid.UUID(share["id"]))

    actions = set(
        db_session.scalars(select(AuditEvent.action).where(AuditEvent.organisation_id == org_a.id)).all()
    )
    assert "council_portal.officer.invite" in actions
    assert "council_portal.share.create" in actions
    assert "council_portal.view" in actions

    # Prove core enum still six after module import
    assert len(HMoreRole) == 6

