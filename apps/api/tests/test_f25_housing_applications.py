"""F2.5 housing applications, waiting lists, and approvals tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.housing.service import APPLICATION_TRANSITIONS
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def test_f25_permissions() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.APPLICATIONS_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.APPLICATIONS_REVIEW)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.WAITING_LIST_MANAGE)
    assert role_has_permission(HMoreRole.TENANT, Permission.APPLICATIONS_CREATE_OWN)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.APPLICATIONS_READ_ASSIGNED)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.APPLICATIONS_MANAGE)
    assert not role_has_permission(HMoreRole.MAINTENANCE_CONTRACTOR, Permission.WAITING_LIST_MANAGE)


def test_application_transitions() -> None:
    assert "submitted" in APPLICATION_TRANSITIONS["draft"]
    assert "approved" not in APPLICATION_TRANSITIONS["draft"]
    assert "approved" in APPLICATION_TRANSITIONS["under_review"]
    assert "closed" in APPLICATION_TRANSITIONS["approved"]


def test_unauthenticated_housing_apis_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/housing-applications").status_code == 401
    assert client.get("/api/v1/waiting-list").status_code == 401


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
def test_housing_application_waiting_list_flow(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, OrganisationMembership, Tenant, User
    from app.housing import service as housing_service
    from app.housing.schemas import ApplicationCreate, DecisionCreate, WaitingListAdd
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Housing Org", slug=f"hous-{unique_suffix}")
    admin = User(
        email=f"oa-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    reviewer = User(
        email=f"rev-{unique_suffix}@example.com",
        display_name="Reviewer",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    worker = User(
        email=f"sw-{unique_suffix}@example.com",
        display_name="Worker",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, admin, reviewer, worker])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id,
        preferred_name="Applicant",
        status=RecordStatus.ACTIVE,
    )
    db_session.add(tenant)
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
                user_id=reviewer.id,
                organisation_id=org.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=worker.id,
                organisation_id=org.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()
    apply_organisation_rls(db_session, org.id)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    reviewer_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, reviewer.id)

    app_row = housing_service.create_application(
        db_session,
        admin_ctx,
        ApplicationCreate(
            tenant_id=tenant.id,
            housing_requirements="Need single room near support services",
            priority="high",
            submit=True,
        ),
    )
    assert app_row.status == "submitted"
    assert app_row.reference_number.startswith("APP-")

    with pytest.raises(HTTPException):
        housing_service.transition_application(db_session, admin_ctx, app_row.id, "approved")

    # Creator cannot decide their own application
    with pytest.raises(HTTPException) as sod:
        housing_service.record_decision(
            db_session,
            admin_ctx,
            app_row.id,
            DecisionCreate(decision="approved", decision_notes="ok", add_to_waiting_list=True),
        )
    assert sod.value.status_code == 403

    housing_service.transition_application(db_session, reviewer_ctx, app_row.id, "under_review")
    decision = housing_service.record_decision(
        db_session,
        reviewer_ctx,
        app_row.id,
        DecisionCreate(decision="approved", decision_notes="Eligible", add_to_waiting_list=True),
    )
    assert decision.decision == "approved"

    refreshed = housing_service.get_application(db_session, admin_ctx, app_row.id)
    assert refreshed.status == "approved"

    entries, total = housing_service.list_waiting_list(
        db_session, admin_ctx, page=1, page_size=20
    )
    assert total >= 1
    assert any(e.application_id == app_row.id for e in entries)
    assert entries[0].position >= 1

    # Duplicate waiting-list add rejected
    with pytest.raises(HTTPException) as dup:
        housing_service.add_to_waiting_list(
            db_session, admin_ctx, WaitingListAdd(application_id=app_row.id)
        )
    assert dup.value.status_code == 409

    # Org isolation: other org cannot see application
    other = Organisation(name="Other", slug=f"other-{unique_suffix}")
    db_session.add(other)
    db_session.flush()
    other_admin = User(
        email=f"oa2-{unique_suffix}@example.com",
        display_name="Other Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add(other_admin)
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=other_admin.id,
            organisation_id=other.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    apply_organisation_rls(db_session, other.id)
    other_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, other_admin.id)
    with pytest.raises(HTTPException) as iso:
        housing_service.get_application(db_session, other_ctx, app_row.id)
    assert iso.value.status_code == 404

