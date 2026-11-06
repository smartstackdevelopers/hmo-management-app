"""F2.1 caseload, daily log, and handover tests."""

from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.support.schemas import DailyLogCreate, HandoverCreate
from app.tenancy.context import OrganisationContext


def test_support_permissions_matrix() -> None:
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.SUPPORT_NOTES_CREATE_ASSIGNED)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.SUPPORT_NOTES_READ_ASSIGNED)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.SUPPORT_NOTES_READ_ASSIGNED)
    assert not role_has_permission(HMoreRole.TENANT, Permission.SUPPORT_NOTES_CREATE_ASSIGNED)


def test_daily_log_schema_rejects_blank_and_bad_category() -> None:
    with pytest.raises(ValidationError):
        DailyLogCreate(
            tenant_id=uuid.uuid4(),
            activity_category="not_a_real_category",
            summary="x",
            notes="y",
        )
    with pytest.raises(ValidationError):
        DailyLogCreate(
            tenant_id=uuid.uuid4(),
            activity_category="keywork",
            summary="   ",
            notes="body",
        )


def test_handover_schema_requires_summary() -> None:
    with pytest.raises(ValidationError):
        HandoverCreate(
            tenant_id=uuid.uuid4(),
            recipient_user_id=uuid.uuid4(),
            summary="  ",
        )


def test_unauthenticated_support_apis_return_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/caseload").status_code == 401
    assert client.post(
        "/api/v1/daily-logs",
        json={
            "tenant_id": str(uuid.uuid4()),
            "activity_category": "keywork",
            "summary": "s",
            "notes": "n",
        },
    ).status_code == 401
    assert client.get("/api/v1/handovers").status_code == 401


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
def test_caseload_logs_handovers_isolation(db_session, unique_suffix: str) -> None:
    from app.db.models import (
        Organisation,
        OrganisationMembership,
        Tenant,
        User,
    )
    from app.support.schemas import CaseAssignmentCreate, DailyLogCreate, DailyLogUpdate, HandoverCreate
    from app.support import service as support_service
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="SA", slug=f"sa-{unique_suffix}")
    org_b = Organisation(name="SB", slug=f"sb-{unique_suffix}")
    admin = User(
        email=f"admin-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    worker = User(
        email=f"sw-{unique_suffix}@example.com",
        display_name="Worker",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    worker2 = User(
        email=f"sw2-{unique_suffix}@example.com",
        display_name="Worker2",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    other_worker = User(
        email=f"swb-{unique_suffix}@example.com",
        display_name="Other",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, admin, worker, worker2, other_worker])
    db_session.flush()

    tenant_a = Tenant(
        organisation_id=org_a.id,
        preferred_name="Ali",
        full_name="Ali Example",
        tenancy_reference=f"T-{unique_suffix}",
        status=RecordStatus.ACTIVE,
    )
    tenant_b = Tenant(
        organisation_id=org_b.id,
        preferred_name="Bob",
        status=RecordStatus.ACTIVE,
    )
    db_session.add_all(
        [
            tenant_a,
            tenant_b,
            OrganisationMembership(
                user_id=admin.id,
                organisation_id=org_a.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=worker.id,
                organisation_id=org_a.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=worker2.id,
                organisation_id=org_a.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=other_worker.id,
                organisation_id=org_b.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()

    apply_organisation_rls(db_session, org_a.id)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin.id)
    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org_a.id, worker.id)
    worker2_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org_a.id, worker2.id)

    assignment = support_service.create_assignment(
        db_session,
        admin_ctx,
        CaseAssignmentCreate(tenant_id=tenant_a.id, support_worker_user_id=worker.id),
    )
    assert assignment["status"] == "active"

    # Worker cannot self-assign
    with pytest.raises(HTTPException) as exc:
        support_service.create_assignment(
            db_session,
            worker_ctx,
            CaseAssignmentCreate(tenant_id=tenant_a.id, support_worker_user_id=worker2.id),
        )
    assert exc.value.status_code == 403

    # Unassigned worker denied tenant case
    with pytest.raises(HTTPException) as denied:
        support_service.get_case_detail(db_session, worker2_ctx, tenant_a.id)
    assert denied.value.status_code == 403

    items, total = support_service.list_caseload(db_session, worker_ctx, page=1, page_size=20)
    assert total == 1
    assert items[0]["tenant_id"] == tenant_a.id

    log = support_service.create_daily_log(
        db_session,
        worker_ctx,
        DailyLogCreate(
            tenant_id=tenant_a.id,
            activity_category="keywork",
            summary="Morning check",
            notes="Stable presentation. No crisis indicators noted.",
            interaction_type="in_person",
            follow_up_required=True,
            next_action="Book housing appointment",
            log_date=date.today(),
        ),
    )
    assert log.author_user_id == worker.id

    # Unassigned worker cannot create log
    with pytest.raises(HTTPException):
        support_service.create_daily_log(
            db_session,
            worker2_ctx,
            DailyLogCreate(
                tenant_id=tenant_a.id,
                activity_category="keywork",
                summary="Nope",
                notes="Should fail",
            ),
        )

    # Author can amend
    updated = support_service.update_daily_log(
        db_session,
        worker_ctx,
        log.id,
        DailyLogUpdate(summary="Morning check (amended)"),
    )
    assert updated.status == "amended"

    # Cross-org denial for Org Admin of A against tenant B
    with pytest.raises(HTTPException) as cross:
        support_service.get_case_detail(db_session, admin_ctx, tenant_b.id)
    assert cross.value.status_code in {403, 404}

    # Handover workflow
    handover = support_service.create_handover(
        db_session,
        worker_ctx,
        HandoverCreate(
            tenant_id=tenant_a.id,
            recipient_user_id=worker2.id,
            summary="Evening handover",
            case_updates="Needs housing follow-up",
            outstanding_tasks="Call housing officer",
            priority="high",
            submit=True,
        ),
    )
    assert handover.status == "submitted"

    # Wrong recipient cannot acknowledge
    with pytest.raises(HTTPException):
        support_service.transition_handover(
            db_session, worker_ctx, handover.id, target_status="acknowledged"
        )

    # Assign worker2 as well so they can access the case, then acknowledge
    support_service.create_assignment(
        db_session,
        admin_ctx,
        CaseAssignmentCreate(tenant_id=tenant_a.id, support_worker_user_id=worker2.id),
    )
    acked = support_service.transition_handover(
        db_session, worker2_ctx, handover.id, target_status="acknowledged"
    )
    assert acked.status == "acknowledged"
    assert acked.acknowledged_by_user_id == worker2.id

    completed = support_service.transition_handover(
        db_session, worker2_ctx, handover.id, target_status="completed"
    )
    assert completed.status == "completed"

    # Invalid transition
    with pytest.raises(HTTPException):
        support_service.transition_handover(
            db_session, worker2_ctx, handover.id, target_status="submitted"
        )
