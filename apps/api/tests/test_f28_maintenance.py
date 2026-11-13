"""F2.8 maintenance workflow, permissions, and isolation tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import AuditEvent, Organisation, OrganisationMembership, Property, Tenant, User
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.main import app
from app.maintenance import service as msvc
from app.maintenance.schemas import AssignRequest, CompleteRequest, MaintenanceCreate, StatusTransitionRequest
from app.maintenance.service import MAINT_TRANSITIONS
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def test_f28_permissions() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.MAINTENANCE_MANAGE)
    assert role_has_permission(HMoreRole.TENANT, Permission.MAINTENANCE_CREATE_OWN)
    assert role_has_permission(HMoreRole.LANDLORD, Permission.MAINTENANCE_PHOTO_READ)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.MAINTENANCE_READ_ASSIGNED)
    assert not role_has_permission(HMoreRole.TENANT, Permission.MAINTENANCE_MANAGE)


def test_maintenance_transitions() -> None:
    assert "acknowledged" in MAINT_TRANSITIONS["submitted"]
    # Graph may list `completed` from in_progress; callers must use POST .../complete instead.
    assert "completed" in MAINT_TRANSITIONS["in_progress"]
    assert len(MAINT_TRANSITIONS["cancelled"]) == 0


def test_unauthenticated_maintenance_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/maintenance").status_code == 401
    assert client.get("/api/v1/maintenance/dashboard").status_code == 401


def _ctx(role: HMoreRole, org_id: uuid.UUID, user_id: uuid.UUID) -> OrganisationContext:
    user = SimpleNamespace(
        id=user_id,
        authorization_version=1,
        external_subject=f"auth0|{uuid.uuid4()}",
        email="u@example.com",
        display_name="U",
    )
    authz = AuthorizationContext(
        user=user,  # type: ignore[arg-type]
        memberships=[
            MembershipView(
                membership_id=uuid.uuid4(),
                role=role,
                organisation_id=org_id,
                status=MembershipStatus.ACTIVE,
            )
        ],
        active_organisation_id=org_id,
        active_role=role,
    )
    return OrganisationContext(
        user=user,  # type: ignore[arg-type]
        organisation_id=org_id,
        role=role,
        authorization=authz,
    )


@pytest.mark.postgres
def test_maintenance_isolation_and_workflow(db_session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Maint Org", slug=f"mnt-{unique_suffix}")
    other = Organisation(name="Other Org", slug=f"mnt-o-{unique_suffix}")
    admin = User(
        email=f"oa-m-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    contractor = User(
        email=f"co-m-{unique_suffix}@example.com",
        display_name="Contractor",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    other_admin = User(
        email=f"oa2-m-{unique_suffix}@example.com",
        display_name="Other",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, other, admin, contractor, other_admin])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id,
        preferred_name="T",
        status=RecordStatus.ACTIVE,
        user_id=None,
    )
    prop = Property(
        organisation_id=org.id,
        name="P1",
        address_line1="1 Test St",
        city="London",
        postcode="E1 1AA",
        status=RecordStatus.ACTIVE,
        landlord_user_id=None,
    )
    db_session.add_all([tenant, prop])
    db_session.flush()
    db_session.add_all(
        [
            OrganisationMembership(
                user_id=admin.id,
                organisation_id=org.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=contractor.id,
                organisation_id=org.id,
                role=HMoreRole.MAINTENANCE_CONTRACTOR,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=other_admin.id,
                organisation_id=other.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()
    apply_organisation_rls(db_session, org.id)

    ctx_a = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    msvc.ensure_defaults(db_session, ctx_a)
    row = msvc.create_request(
        db_session,
        ctx_a,
        MaintenanceCreate(
            title="Leak",
            description="Water under sink",
            category_code="water_leak",
            priority="normal",
            property_id=prop.id,
            tenant_id=tenant.id,
            requires_approval=False,
        ),
    )
    rid = row.id

    msvc.transition_status(
        db_session, ctx_a, rid, StatusTransitionRequest(status="acknowledged", note="ok")
    )
    msvc.assign_request(db_session, ctx_a, rid, AssignRequest(assigned_user_id=contractor.id, note="to contractor"))
    db_session.flush()

    ctx_c = _ctx(HMoreRole.MAINTENANCE_CONTRACTOR, org.id, contractor.id)
    msvc.transition_status(db_session, ctx_c, rid, StatusTransitionRequest(status="in_progress", note="started"))
    msvc.complete_request(
        db_session,
        ctx_c,
        rid,
        CompleteRequest(work_notes="Fixed trap", completion_summary="Replaced washer"),
    )
    db_session.flush()

    audits = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.organisation_id == org.id,
            AuditEvent.action.like("maintenance.%"),
        )
    ).all()
    assert len(audits) >= 1

    apply_organisation_rls(db_session, other.id)
    ctx_other = _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, other_admin.id)
    with pytest.raises(HTTPException) as exc:
        msvc.get_request(db_session, ctx_other, rid)
    assert exc.value.status_code == 404

    apply_organisation_rls(db_session, org.id)
    stats = msvc.dashboard_stats(db_session, ctx_a)
    assert stats["total"] >= 1

