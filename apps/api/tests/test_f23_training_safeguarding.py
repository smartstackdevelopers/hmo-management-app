"""F2.3 training records and safeguarding reminder tests."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.compliance.schemas import TrainingCreate
from app.compliance.service import effective_training_status
from app.db.models.compliance import StaffTrainingRecord
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def test_f23_permissions() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.TRAINING_RECORDS_MANAGE)
    assert role_has_permission(
        HMoreRole.ORGANISATION_ADMIN, Permission.SAFEGUARDING_REMINDERS_MANAGE
    )
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.TRAINING_RECORDS_READ_OWN)
    assert role_has_permission(
        HMoreRole.SUPPORT_WORKER, Permission.SAFEGUARDING_REMINDERS_MANAGE_ASSIGNED
    )
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.TRAINING_RECORDS_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.SAFEGUARDING_REMINDERS_MANAGE)


def test_training_schema_rejects_bad_dates() -> None:
    with pytest.raises(ValidationError):
        TrainingCreate(
            staff_user_id=uuid.uuid4(),
            title="First Aid",
            completion_date=date(2026, 11, 6),
            expiry_date=date(2026, 1, 1),
            status="completed",
        )


def test_effective_status_expired_and_expiring() -> None:
    today = date.today()
    expired = StaffTrainingRecord(
        organisation_id=uuid.uuid4(),
        staff_user_id=uuid.uuid4(),
        title="Safeguarding",
        category="safeguarding",
        status="completed",
        completion_date=today - timedelta(days=400),
        expiry_date=today - timedelta(days=1),
    )
    assert effective_training_status(expired, soon_days=30) == "expired"
    soon = StaffTrainingRecord(
        organisation_id=uuid.uuid4(),
        staff_user_id=uuid.uuid4(),
        title="Fire Safety",
        category="health_safety",
        status="completed",
        completion_date=today - timedelta(days=300),
        expiry_date=today + timedelta(days=7),
    )
    assert effective_training_status(soon, soon_days=30) == "expiring_soon"


def test_unauthenticated_compliance_apis_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/training").status_code == 401
    assert client.get("/api/v1/safeguarding-reminders").status_code == 401


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
def test_training_and_safeguarding_flow(db_session, unique_suffix: str) -> None:
    from app.compliance import service as compliance_service
    from app.compliance.schemas import (
        SafeguardingCreate,
        SafeguardingUpdate,
        TrainingCreate,
        TrainingUpdate,
    )
    from app.db.models import Organisation, OrganisationMembership, Tenant, User
    from app.db.models.support_ops import CaseAssignment
    from app.ops.reminders import dispatch_due_reminders
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Compliance Org", slug=f"comp-{unique_suffix}")
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

    today = date.today()
    training = compliance_service.create_training(
        db_session,
        admin_ctx,
        TrainingCreate(
            staff_user_id=worker.id,
            title="Safeguarding Adults",
            category="safeguarding",
            completion_date=today - timedelta(days=300),
            expiry_date=today + timedelta(days=5),
            status="completed",
        ),
    )
    assert training.status == "completed"
    assert compliance_service.effective_training_status(training, soon_days=30) == "expiring_soon"

    expiring, total = compliance_service.list_training(
        db_session, admin_ctx, page=1, page_size=20, expiring_only=True
    )
    assert total >= 1
    assert any(row.id == training.id for row in expiring)

    # SW cannot manage others' create
    with pytest.raises(HTTPException):
        compliance_service.create_training(
            db_session,
            worker_ctx,
            TrainingCreate(staff_user_id=worker.id, title="x"),
        )

    own, _ = compliance_service.list_training(db_session, worker_ctx, page=1, page_size=20)
    assert any(row.id == training.id for row in own)

    reminder = compliance_service.create_safeguarding(
        db_session,
        admin_ctx,
        SafeguardingCreate(
            title="Review follow-up action",
            category="follow_up",
            description="Open application for details — no case content here.",
            due_at=datetime.now(timezone.utc) + timedelta(hours=2),
            priority="high",
            assigned_user_id=worker.id,
            tenant_id=tenant.id,
        ),
    )
    assert reminder.status == "pending"

    ack = compliance_service.acknowledge_safeguarding(db_session, worker_ctx, reminder.id)
    assert ack.status == "acknowledged"
    assert ack.acknowledged_at is not None

    done = compliance_service.complete_safeguarding(db_session, worker_ctx, reminder.id)
    assert done.status == "completed"

    # Delivery skip for completed safeguarding
    result = dispatch_due_reminders(db_session, limit=50)
    assert "processed" in result

    updated = compliance_service.update_training(
        db_session,
        admin_ctx,
        training.id,
        TrainingUpdate(notes="Renewed annually per org policy"),
    )
    assert updated.notes is not None


def test_safeguarding_transition_rejects_invalid() -> None:
    from app.compliance.service import SAFEGUARDING_TRANSITIONS

    assert "completed" not in SAFEGUARDING_TRANSITIONS["cancelled"]
    assert "acknowledged" in SAFEGUARDING_TRANSITIONS["pending"]
