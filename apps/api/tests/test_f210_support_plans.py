"""F2.10 structured support plans — RBAC, transitions, isolation (PostgreSQL)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import (
    Complaint,
    Organisation,
    OrganisationMembership,
    Property,
    Tenant,
    User,
)
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.rbac.context import AuthorizationContext, MembershipView
from app.support.schemas import CaseAssignmentCreate
from app.support import service as support_service
from app.support_plans.schemas import (
    ExportCreate,
    GoalAchieveBody,
    GoalCreate,
    GoalUpdate,
    MilestoneCompleteBody,
    MilestoneCreate,
    ReviewCreate,
    ReviewUpdate,
    SupportPlanCreate,
    SupportPlanReviseCreate,
)
from app.support_plans import service as sp_service
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


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


def _landlord_ctx(org_id: uuid.UUID, user_id: uuid.UUID) -> OrganisationContext:
    return _ctx(HMoreRole.LANDLORD, org_id, user_id)


@pytest.mark.postgres
def test_f210_plan_lifecycle_and_isolation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)

    org_a = Organisation(name="SPA", slug=f"spa-{unique_suffix}")
    org_b = Organisation(name="SPB", slug=f"spb-{unique_suffix}")
    admin_a = User(
        email=f"oadm-{unique_suffix}@example.com",
        display_name="OA",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    worker_a = User(
        email=f"sw-{unique_suffix}@example.com",
        display_name="SW",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    worker_b = User(
        email=f"swb-{unique_suffix}@example.com",
        display_name="SWB",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    tenant_user = User(
        email=f"tn-{unique_suffix}@example.com",
        display_name="T",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    landlord = User(
        email=f"ll-{unique_suffix}@example.com",
        display_name="L",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, admin_a, worker_a, worker_b, tenant_user, landlord])
    db_session.flush()

    tenant_a = Tenant(
        organisation_id=org_a.id,
        preferred_name="Ali",
        full_name="Ali Example",
        user_id=tenant_user.id,
        tenancy_reference=f"T-{unique_suffix}",
        status=RecordStatus.ACTIVE,
    )
    tenant_b = Tenant(
        organisation_id=org_b.id,
        preferred_name="Other",
        status=RecordStatus.ACTIVE,
    )
    prop = Property(
        organisation_id=org_a.id,
        landlord_user_id=landlord.id,
        name="P1",
        address_line1="1 Road",
        city="London",
        postcode="AB1 2CD",
        status=RecordStatus.ACTIVE,
    )
    db_session.add_all([tenant_a, tenant_b, prop])
    db_session.flush()
    db_session.add(
        Complaint(
            organisation_id=org_a.id,
            reference_number=f"CMP-{unique_suffix}",
            title="Test",
            description="Test complaint",
            category_code="general",
            tenant_id=tenant_a.id,
            property_id=prop.id,
            status="submitted",
            submitted_at=datetime.now(timezone.utc),
        )
    )
    db_session.flush()

    db_session.add_all(
        [
            OrganisationMembership(
                user_id=admin_a.id,
                organisation_id=org_a.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=worker_a.id,
                organisation_id=org_a.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=worker_b.id,
                organisation_id=org_b.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=tenant_user.id,
                organisation_id=org_a.id,
                role=HMoreRole.TENANT,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=landlord.id,
                organisation_id=org_a.id,
                role=HMoreRole.LANDLORD,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()

    apply_organisation_rls(db_session, org_a.id)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin_a.id)
    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org_a.id, worker_a.id)
    tenant_ctx = _ctx(HMoreRole.TENANT, org_a.id, tenant_user.id)
    landlord_c = _landlord_ctx(org_a.id, landlord.id)

    support_service.create_assignment(
        db_session,
        admin_ctx,
        CaseAssignmentCreate(tenant_id=tenant_a.id, support_worker_user_id=worker_a.id),
    )

    plan = sp_service.create_plan(
        db_session,
        worker_ctx,
        SupportPlanCreate(
            tenant_id=tenant_a.id,
            title="Plan A",
            responsible_worker_user_id=worker_a.id,
        ),
    )
    assert plan["status"] == "draft"
    pid = uuid.UUID(plan["id"])

    # Cross-org isolation: Org B worker cannot read org A plan
    apply_organisation_rls(db_session, org_b.id)
    worker_b_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org_b.id, worker_b.id)
    with pytest.raises(HTTPException) as exc:
        sp_service.get_plan(db_session, worker_b_ctx, tenant_a.id, pid)
    assert exc.value.status_code == 404
    apply_organisation_rls(db_session, org_a.id)

    sp_service.activate_plan(db_session, worker_ctx, tenant_a.id, pid)

    g = sp_service.create_goal(
        db_session,
        worker_ctx,
        tenant_a.id,
        pid,
        GoalCreate(title="G1", description="desc"),
    )
    gid = uuid.UUID(g["id"])
    sp_service.update_goal(
        db_session,
        worker_ctx,
        tenant_a.id,
        pid,
        gid,
        GoalUpdate(status="in_progress"),
    )

    ms = sp_service.create_milestone(
        db_session,
        worker_ctx,
        tenant_a.id,
        pid,
        gid,
        MilestoneCreate(title="M1", target_date=date.today() - timedelta(days=1)),
    )
    mid = uuid.UUID(ms["id"])

    dash = sp_service.progress_dashboard(
        db_session,
        worker_ctx,
        tenant_id=None,
        worker_user_id=None,
        plan_status=None,
        review_period_start=None,
        review_period_end=None,
    )
    assert dash["overdue_milestones"] >= 1

    rev = sp_service.create_review(
        db_session,
        worker_ctx,
        tenant_a.id,
        pid,
        ReviewCreate(
            review_type="weekly",
            review_date=date.today(),
            progress_summary="ok",
            status="draft",
        ),
    )
    rid = uuid.UUID(rev["id"])
    sp_service.update_review(
        db_session,
        worker_ctx,
        tenant_a.id,
        pid,
        rid,
        ReviewUpdate(status="in_progress"),
    )
    fin = sp_service.finalise_review(db_session, worker_ctx, tenant_a.id, pid, rid)
    assert fin["status"] == "finalised"

    with pytest.raises(HTTPException) as exc:
        sp_service.update_review(
            db_session,
            worker_ctx,
            tenant_a.id,
            pid,
            rid,
            ReviewUpdate(progress_summary="nope"),
        )
    assert exc.value.status_code == 409

    sp_service.complete_milestone(
        db_session,
        worker_ctx,
        tenant_a.id,
        pid,
        gid,
        mid,
        MilestoneCompleteBody(completion_notes="done"),
    )
    sp_service.achieve_goal(
        db_session,
        worker_ctx,
        tenant_a.id,
        pid,
        gid,
        GoalAchieveBody(),
    )

    exp = sp_service.create_progress_export(
        db_session,
        worker_ctx,
        tenant_a.id,
        pid,
        ExportCreate(include_internal=False),
    )
    assert "file" in exp

    # Tenant read-only sees plan without internal
    t_plan = sp_service.get_plan(db_session, tenant_ctx, tenant_a.id, pid)
    assert t_plan["internal_notes"] is None

    # Landlord with property scope
    ll_plan = sp_service.get_plan(db_session, landlord_c, tenant_a.id, pid)
    assert ll_plan["id"] == plan["id"]

    # Revise creates new draft
    new_p = sp_service.revise_plan(
        db_session,
        admin_ctx,
        tenant_a.id,
        pid,
        SupportPlanReviseCreate(title="Plan B", responsible_worker_user_id=worker_a.id),
    )
    assert new_p["supersedes_plan_id"] == str(pid)
    assert new_p["status"] == "draft"


def test_pdf_generation_unit() -> None:
    from app.evidence.pdf import build_simple_pdf

    b = build_simple_pdf("T", ["line1", "line2"])
    assert b.startswith(b"%PDF")


def test_plan_status_transition_validation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name="SPT", slug=f"spt-{unique_suffix}")
    admin = User(
        email=f"adm-{unique_suffix}@example.com",
        display_name="A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    sw = User(
        email=f"sw-{unique_suffix}@example.com",
        display_name="W",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, admin, sw])
    db_session.flush()
    t = Tenant(
        organisation_id=org.id,
        preferred_name="X",
        status=RecordStatus.ACTIVE,
    )
    db_session.add_all(
        [
            t,
            OrganisationMembership(
                user_id=admin.id,
                organisation_id=org.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=sw.id,
                organisation_id=org.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()
    apply_organisation_rls(db_session, org.id)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    sw_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, sw.id)
    support_service.create_assignment(
        db_session,
        ctx,
        CaseAssignmentCreate(tenant_id=t.id, support_worker_user_id=sw.id),
    )
    p = sp_service.create_plan(
        db_session,
        sw_ctx,
        SupportPlanCreate(
            tenant_id=t.id,
            title="P",
            responsible_worker_user_id=sw.id,
        ),
    )
    pid = uuid.UUID(p["id"])
    sp_service.activate_plan(db_session, sw_ctx, t.id, pid)
    with pytest.raises(HTTPException) as exc:
        sp_service.activate_plan(db_session, sw_ctx, t.id, pid)
    assert exc.value.status_code == 409
