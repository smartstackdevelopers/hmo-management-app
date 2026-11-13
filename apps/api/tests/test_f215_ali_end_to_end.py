"""F2.15 Ali end-to-end journey (human workflow, no AI)."""

from __future__ import annotations

import importlib
import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import AuditEvent, Organisation, OrganisationMembership, Property, Tenant, User
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.journeys.ali import ALI_JOURNEY_ID, ALI_JOURNEY_STEPS
from app.maintenance.schemas import ApprovalDecisionRequest, MaintenanceCreate
from app.maintenance import service as msvc
from app.org_workflows.inbox import collect_inbox_items
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.permissions import Permission
from app.reporting.dashboard import main_dashboard
from app.support.schemas import CaseAssignmentCreate, DailyLogCreate
from app.support import service as support_service
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def test_ali_journey_definition_non_ai() -> None:
    assert ALI_JOURNEY_ID
    assert len(ALI_JOURNEY_STEPS) >= 4
    steps = {s["order"] for s in ALI_JOURNEY_STEPS}
    assert steps == set(range(1, len(ALI_JOURNEY_STEPS) + 1))
    journeys = importlib.import_module("app.journeys.ali")
    source = journeys.__file__ or ""
    assert source
    with open(source, encoding="utf-8") as fh:
        text = fh.read().lower()
    assert "langgraph" not in text
    assert "openai" not in text


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
def test_f215_ali_journey_full_human_workflow(db_session, unique_suffix: str) -> None:
    """Synthetic Ali: caseload note → maintenance approval (no AI)."""
    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Elm Road Org", slug=f"elm-{unique_suffix}")
    org_b = Organisation(name="Other Org", slug=f"oth-{unique_suffix}")
    admin = User(
        email=f"admin-{unique_suffix}@example.com",
        display_name="Org Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    jade = User(
        email=f"jade-{unique_suffix}@example.com",
        display_name="Jade Reid",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    intruder = User(
        email=f"int-{unique_suffix}@example.com",
        display_name="Intruder",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, org_b, admin, jade, intruder])
    db_session.flush()

    ali = Tenant(
        organisation_id=org.id,
        preferred_name="Ali",
        full_name="Ali Hassan (test)",
        tenancy_reference=f"ALI-{unique_suffix}",
        status=RecordStatus.ACTIVE,
    )
    prop = Property(
        organisation_id=org.id,
        name="Elm Road House",
        address_line1="Elm Road",
        city="Testville",
        postcode="TE1 1ST",
        status=RecordStatus.ACTIVE,
    )
    db_session.add_all([ali, prop])
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
                user_id=jade.id,
                organisation_id=org.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=intruder.id,
                organisation_id=org_b.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()

    apply_organisation_rls(db_session, org.id)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    jade_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, jade.id)

    # Step 1 — caseload assignment
    support_service.create_assignment(
        db_session,
        admin_ctx,
        CaseAssignmentCreate(tenant_id=ali.id, support_worker_user_id=jade.id),
    )

    # Step 2 — daily log (human note, not AI summary)
    log = support_service.create_daily_log(
        db_session,
        jade_ctx,
        DailyLogCreate(
            tenant_id=ali.id,
            activity_category="keywork",
            summary="Tenant reported water leak under sink",
            notes="Ali reported leak this morning. No AI analysis — staff-authored note only.",
            interaction_type="in_person",
            follow_up_required=True,
            next_action="Raise maintenance request",
            log_date=date.today(),
        ),
    )
    assert log.tenant_id == ali.id

    # Step 3 — maintenance (approval required)
    msvc.ensure_defaults(db_session, admin_ctx)
    req = msvc.create_request(
        db_session,
        jade_ctx,
        MaintenanceCreate(
            title="Water leak under sink",
            description="Urgent repair — Room 14 kitchen",
            category_code="water_leak",
            priority="urgent",
            property_id=prop.id,
            tenant_id=ali.id,
            requires_approval=True,
        ),
    )
    assert req.status == "awaiting_approval"

    # RBAC: support worker cannot approve
    with pytest.raises(HTTPException) as denied:
        msvc.record_approval(
            db_session,
            jade_ctx,
            req.id,
            ApprovalDecisionRequest(decision="approved", reason="n/a"),
        )
    assert denied.value.status_code == 403

    # Step 4 — admin approval
    approved = msvc.record_approval(
        db_session,
        admin_ctx,
        req.id,
        ApprovalDecisionRequest(decision="approved", reason="Approved — arrange plumber"),
    )
    assert approved.status == "approved"

    # Step 5 — aggregated inbox sees completed item only when still pending;
    # after approval, inbox should not list awaiting_approval
    inbox = collect_inbox_items(db_session, admin_ctx, source_type="maintenance_request")
    assert all(i["source_id"] != str(req.id) or i["status"] != "pending" for i in inbox)

    # Step 6 — reporting dashboard (org admin)
    dash = main_dashboard(db_session, admin_ctx)
    assert "generated_at" in dash

    audits = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.organisation_id == org.id,
            AuditEvent.action.in_(
                (
                    "daily_log.create",
                    "maintenance.create",
                    "maintenance.approval",
                )
            ),
        )
    ).all()
    assert len(audits) >= 2

    # Organisation isolation
    apply_organisation_rls(db_session, org_b.id)
    intruder_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, intruder.id)
    with pytest.raises(HTTPException):
        msvc.get_request(db_session, intruder_ctx, req.id)


def test_tenant_cannot_export_reports() -> None:
    from app.rbac.matrix import role_has_permission

    assert not role_has_permission(HMoreRole.TENANT, Permission.REPORTS_EXPORT_CSV)
    assert not role_has_permission(HMoreRole.TENANT, Permission.REPORTS_DASHBOARD_VIEW)

