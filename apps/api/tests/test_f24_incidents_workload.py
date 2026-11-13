"""F2.4 incident reports, follow-ups, and workload tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.incidents.service import FOLLOW_UP_TRANSITIONS, INCIDENT_TRANSITIONS
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def test_f24_permissions() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.INCIDENTS_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.WORKLOAD_READ)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.INCIDENTS_CREATE_ASSIGNED)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.INCIDENTS_READ_ASSIGNED)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.WORKLOAD_READ_OWN)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.INCIDENTS_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.WORKLOAD_READ)


def test_incident_and_follow_up_transitions() -> None:
    assert "submitted" in INCIDENT_TRANSITIONS["draft"]
    assert "closed" not in INCIDENT_TRANSITIONS["draft"]
    assert "reopened" in INCIDENT_TRANSITIONS["closed"]
    assert "completed" in FOLLOW_UP_TRANSITIONS["open"]
    assert "open" not in FOLLOW_UP_TRANSITIONS["completed"]


def test_unauthenticated_incident_apis_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/incidents").status_code == 401
    assert client.get("/api/v1/incident-follow-ups").status_code == 401
    assert client.get("/api/v1/workload").status_code == 401


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
def test_incident_follow_up_workload_flow(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, OrganisationMembership, Tenant, User
    from app.db.models.support_ops import CaseAssignment
    from app.incidents import service as incident_service
    from app.incidents.schemas import FollowUpCreate, FollowUpUpdate, IncidentCreate, IncidentUpdate
    from app.ops.reminders import dispatch_due_reminders
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Inc Org", slug=f"inc-{unique_suffix}")
    admin = User(
        email=f"oa-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    worker = User(
        email=f"sw-{unique_suffix}@example.com",
        display_name="Worker",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, admin, worker])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id,
        preferred_name="Casey",
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
                user_id=worker.id,
                organisation_id=org.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
            CaseAssignment(
                organisation_id=org.id,
                tenant_id=tenant.id,
                support_worker_user_id=worker.id,
                assigned_by_user_id=admin.id,
                status="active",
                assigned_at=datetime.now(timezone.utc),
            ),
        ]
    )
    db_session.flush()
    apply_organisation_rls(db_session, org.id)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, worker.id)

    incident = incident_service.create_incident(
        db_session,
        worker_ctx,
        IncidentCreate(
            title="Property damage",
            category="property",
            description="Window broken in communal area",
            occurred_at=datetime.now(timezone.utc) - timedelta(hours=2),
            severity="high",
            tenant_id=tenant.id,
            submit=True,
        ),
    )
    assert incident.status == "submitted"
    assert incident.reference_number.startswith("INC-")

    # Invalid transition
    with pytest.raises(HTTPException):
        incident_service.transition_incident(db_session, admin_ctx, incident.id, "closed")

    incident_service.update_incident(
        db_session,
        admin_ctx,
        incident.id,
        IncidentUpdate(reviewer_user_id=admin.id, status="under_review"),
    )

    follow = incident_service.create_follow_up(
        db_session,
        admin_ctx,
        incident.id,
        FollowUpCreate(
            description="Arrange glazier",
            assigned_user_id=worker.id,
            priority="high",
            due_at=datetime.now(timezone.utc) - timedelta(hours=1),
        ),
    )
    assert follow.status == "open"

    overdue, total = incident_service.list_follow_ups(
        db_session, admin_ctx, page=1, page_size=20, overdue_only=True
    )
    assert total >= 1
    assert any(row.id == follow.id for row in overdue)

    # Cannot close with open follow-ups
    incident_service.update_incident(
        db_session,
        admin_ctx,
        incident.id,
        IncidentUpdate(status="resolved", resolution_notes="Repair scheduled"),
    )
    with pytest.raises(HTTPException) as blocked:
        incident_service.transition_incident(db_session, admin_ctx, incident.id, "closed")
    assert blocked.value.status_code == 400

    incident_service.update_follow_up(
        db_session, worker_ctx, follow.id, FollowUpUpdate(status="completed")
    )
    closed = incident_service.transition_incident(db_session, admin_ctx, incident.id, "closed")
    assert closed.status == "closed"

    reopened = incident_service.transition_incident(db_session, admin_ctx, incident.id, "reopened")
    assert reopened.status == "reopened"

    workload = incident_service.get_workload(db_session, worker_ctx)
    assert workload.scope == "own"
    assert any(row.staff_user_id == worker.id for row in workload.staff)

    org_workload = incident_service.get_workload(db_session, admin_ctx)
    assert org_workload.scope == "organisation"

    result = dispatch_due_reminders(db_session, limit=50)
    assert "processed" in result

