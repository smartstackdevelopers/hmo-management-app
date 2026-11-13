"""F2.2 rota, visits, tasks, and reminder tests."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.main import app
from app.ops.schemas import ShiftCreate, TaskCreate, VisitCreate
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext
from app.workers.celery_app import celery_app


def test_f22_permissions() -> None:
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.VISITS_MANAGE_ASSIGNED)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.TASKS_MANAGE_ASSIGNED)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.VISITS_MANAGE_ASSIGNED)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.TASKS_MANAGE_ASSIGNED)


def test_shift_schema_rejects_invalid_window() -> None:
    start = datetime(2026, 11, 6, 9, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        ShiftCreate(
            staff_user_id=uuid.uuid4(),
            shift_date=date(2026, 11, 6),
            starts_at=start,
            ends_at=start,
        )


def test_celery_reminder_tasks_registered() -> None:
    assert "hmore.reminders.dispatch_due" in celery_app.tasks
    assert "hmore.reminders.dispatch_organisation" in celery_app.tasks


def test_unauthenticated_ops_apis_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/shifts").status_code == 401
    assert client.get("/api/v1/visits").status_code == 401
    assert client.get("/api/v1/tasks").status_code == 401
    assert client.get("/api/v1/reminders").status_code == 401


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
def test_rota_visits_tasks_reminders_flow(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, OrganisationMembership, Tenant, User
    from app.db.models.support_ops import CaseAssignment
    from app.ops import service as ops_service
    from app.ops.reminders import dispatch_due_reminders
    from app.ops.schemas import ShiftCancel, ShiftCreate, TaskCreate, TaskUpdate, VisitCreate, VisitUpdate
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Ops", slug=f"ops-{unique_suffix}")
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

    start = datetime.now(timezone.utc) + timedelta(hours=3)
    end = start + timedelta(hours=8)
    shift = ops_service.create_shift(
        db_session,
        admin_ctx,
        ShiftCreate(
            staff_user_id=worker.id,
            shift_date=start.date(),
            starts_at=start,
            ends_at=end,
        ),
    )
    assert shift.status == "scheduled"

    # Overlap rejected
    with pytest.raises(HTTPException) as overlap:
        ops_service.create_shift(
            db_session,
            admin_ctx,
            ShiftCreate(
                staff_user_id=worker.id,
                shift_date=start.date(),
                starts_at=start + timedelta(hours=1),
                ends_at=end + timedelta(hours=1),
            ),
        )
    assert overlap.value.status_code == 409

    visit = ops_service.create_visit(
        db_session,
        worker_ctx,
        VisitCreate(
            tenant_id=tenant.id,
            assigned_staff_user_id=worker.id,
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=4),
            purpose="Welfare check",
        ),
    )
    assert visit.status == "scheduled"

    # SW cannot assign visit to someone else
    with pytest.raises(HTTPException):
        ops_service.create_visit(
            db_session,
            worker_ctx,
            VisitCreate(
                tenant_id=tenant.id,
                assigned_staff_user_id=admin.id,
                scheduled_at=datetime.now(timezone.utc) + timedelta(hours=5),
                purpose="Bad",
            ),
        )

    completed = ops_service.update_visit(
        db_session,
        worker_ctx,
        visit.id,
        VisitUpdate(status="completed", outcome="All well"),
    )
    assert completed.status == "completed"

    task = ops_service.create_task(
        db_session,
        worker_ctx,
        TaskCreate(
            title="Follow up housing",
            assigned_user_id=worker.id,
            tenant_id=tenant.id,
            priority="high",
            due_at=datetime.now(timezone.utc) - timedelta(hours=1),
        ),
    )
    overdue, total = ops_service.list_tasks(
        db_session, worker_ctx, page=1, page_size=20, overdue_only=True
    )
    assert total >= 1
    assert any(row.id == task.id for row in overdue)

    done = ops_service.update_task(
        db_session, worker_ctx, task.id, TaskUpdate(status="completed")
    )
    assert done.status == "completed"

    cancelled = ops_service.cancel_shift(
        db_session, admin_ctx, shift.id, ShiftCancel(cancel_reason="Staff illness")
    )
    assert cancelled.status == "cancelled"

    # Reminder dispatch skips cancelled shift reminders
    result = dispatch_due_reminders(db_session, limit=50)
    assert "processed" in result


@pytest.mark.postgres
def test_notification_provider_in_app_delivery(db_session: Session) -> None:
    """F2.12 provider persists in-app deliveries with explicit idempotency."""
    from app.db.models import Organisation, User
    from app.ops.notifications import ReminderMessage, get_notification_provider
    from app.tenancy.session_rls import apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="NP", slug=f"np-{uuid.uuid4().hex[:8]}")
    user = User(email=f"np-{uuid.uuid4().hex[:8]}@example.com", display_name="N", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add_all([org, user])
    db_session.flush()

    provider = get_notification_provider()
    result = provider.send(
        db_session,
        ReminderMessage(
            organisation_id=str(org.id),
            recipient_user_id=str(user.id),
            subject="Test",
            body="Body",
            channel="in_app",
            target_type="reminder_record",
            target_id=str(uuid.uuid4()),
            idempotency_key=f"test:{uuid.uuid4()}",
            essential_operational=True,
        ),
    )
    assert result.success is True
    assert result.provider == "in_app_store"

