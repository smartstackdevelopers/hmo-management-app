"""F2.7 complaints workflow, deadlines, escalations, isolation tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.complaints.jobs import process_overdue_escalations_for_org
from app.complaints.service import COMPLAINT_TRANSITIONS, is_overdue
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def test_f27_permissions() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.COMPLAINTS_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.COMPLAINTS_ESCALATE)
    assert role_has_permission(HMoreRole.TENANT, Permission.COMPLAINTS_CREATE_OWN)
    assert role_has_permission(HMoreRole.TENANT, Permission.COMPLAINTS_READ_OWN)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.COMPLAINTS_READ_ASSIGNED)
    assert role_has_permission(HMoreRole.LANDLORD, Permission.COMPLAINTS_READ_PROPERTY)
    assert not role_has_permission(HMoreRole.MAINTENANCE_CONTRACTOR, Permission.COMPLAINTS_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.COMPLAINTS_NOTES_INTERNAL)


def test_complaint_transitions() -> None:
    assert "acknowledged" in COMPLAINT_TRANSITIONS["submitted"]
    assert "closed" not in COMPLAINT_TRANSITIONS["submitted"]
    assert "reopened" in COMPLAINT_TRANSITIONS["closed"]
    assert len(COMPLAINT_TRANSITIONS["withdrawn"]) == 0


def test_is_overdue_unit() -> None:
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        status="investigation",
        response_due_at=now - timedelta(hours=1),
        acknowledge_due_at=None,
        acknowledged_at=None,
    )
    assert is_overdue(row, now) is True
    row.status = "closed"
    assert is_overdue(row, now) is False


def test_unauthenticated_complaints_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/complaints").status_code == 401
    assert client.get("/api/v1/complaints/dashboard").status_code == 401


def test_celery_complaint_task_registered() -> None:
    from app.workers.celery_app import celery_app

    assert "hmore.complaints.dispatch_overdue" in celery_app.tasks
    assert "hmore.complaints.dispatch_organisation_overdue" in celery_app.tasks


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
def test_complaints_workflow_notes_escalation_isolation(
    db_session, unique_suffix: str
) -> None:
    from app.complaints import service as complaint_service
    from app.complaints.schemas import (
        ComplaintCreate,
        EscalateRequest,
        NoteCreate,
        PriorityRequest,
        ResolveEscalationRequest,
        StatusTransitionRequest,
    )
    from app.db.models import Organisation, OrganisationMembership, Tenant, User
    from app.db.models.audit import AuditEvent
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass
    from sqlalchemy import select

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Complaints Org", slug=f"cmp-{unique_suffix}")
    other = Organisation(name="Other Org", slug=f"cmp-o-{unique_suffix}")
    admin = User(
        email=f"oa-c-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    tenant_user = User(
        email=f"tn-c-{unique_suffix}@example.com",
        display_name="Tenant",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    other_admin = User(
        email=f"oa2-c-{unique_suffix}@example.com",
        display_name="Other",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, other, admin, tenant_user, other_admin])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id,
        preferred_name="Complainant",
        status=RecordStatus.ACTIVE,
        user_id=tenant_user.id,
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
                user_id=tenant_user.id,
                organisation_id=org.id,
                role=HMoreRole.TENANT,
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
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    tenant_ctx = _ctx(HMoreRole.TENANT, org.id, tenant_user.id)

    complaint_service.ensure_defaults(db_session, admin_ctx)
    complaint = complaint_service.create_complaint(
        db_session,
        tenant_ctx,
        ComplaintCreate(title="Noise issue", description="Ongoing disturbance at night", priority="high"),
    )
    assert complaint.reference_number.startswith("CMP-")
    assert complaint.status == "submitted"
    assert complaint.response_due_at is not None

    with pytest.raises(HTTPException):
        complaint_service.transition_status(
            db_session,
            admin_ctx,
            complaint.id,
            StatusTransitionRequest(status="closed", note="too soon"),
        )

    complaint_service.transition_status(
        db_session,
        admin_ctx,
        complaint.id,
        StatusTransitionRequest(status="acknowledged", note="Ack"),
    )
    complaint_service.change_priority(
        db_session,
        admin_ctx,
        complaint.id,
        PriorityRequest(priority="urgent", reason="Safety concern"),
    )

    internal = complaint_service.add_note(
        db_session,
        admin_ctx,
        complaint.id,
        NoteCreate(body="Internal investigation detail", visibility="internal"),
    )
    visible = complaint_service.add_note(
        db_session,
        admin_ctx,
        complaint.id,
        NoteCreate(body="We are reviewing your complaint", visibility="tenant_visible"),
    )
    tenant_notes = complaint_service.list_notes(db_session, tenant_ctx, complaint.id)
    assert all(n.visibility == "tenant_visible" for n in tenant_notes)
    assert visible.id in {n.id for n in tenant_notes}
    assert internal.id not in {n.id for n in tenant_notes}

    esc = complaint_service.escalate_complaint(
        db_session,
        admin_ctx,
        complaint.id,
        EscalateRequest(reason="Needs senior review", idempotency_key="manual-1"),
    )
    dup = complaint_service.escalate_complaint(
        db_session,
        admin_ctx,
        complaint.id,
        EscalateRequest(reason="Needs senior review", idempotency_key="manual-1"),
    )
    assert dup.id == esc.id

    complaint_service.resolve_escalation(
        db_session,
        admin_ctx,
        esc.id,
        ResolveEscalationRequest(outcome="Assigned senior officer"),
    )

    # Force overdue and run idempotent job twice
    refreshed = complaint_service.get_complaint(db_session, admin_ctx, complaint.id)
    refreshed.response_due_at = datetime.now(timezone.utc) - timedelta(days=1)
    refreshed.status = "investigation"
    db_session.flush()
    first = process_overdue_escalations_for_org(db_session, org.id)
    second = process_overdue_escalations_for_org(db_session, org.id)
    assert first["created"] >= 1
    assert second["created"] == 0
    assert second["skipped"] >= 1

    audits = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.organisation_id == org.id,
            AuditEvent.action.like("complaint.%"),
        )
    ).all()
    assert len(audits) >= 3

    apply_organisation_rls(db_session, other.id)
    other_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, other_admin.id)
    with pytest.raises(HTTPException) as iso:
        complaint_service.get_complaint(db_session, other_ctx, complaint.id)
    assert iso.value.status_code == 404
    with pytest.raises(HTTPException):
        complaint_service.list_notes(db_session, other_ctx, complaint.id)
    with pytest.raises(HTTPException):
        complaint_service.escalate_complaint(
            db_session,
            other_ctx,
            complaint.id,
            EscalateRequest(reason="cross org"),
        )


@pytest.mark.postgres
def test_maintenance_denied_complaints(db_session, unique_suffix: str) -> None:
    from app.complaints import service as complaint_service
    from app.complaints.schemas import ComplaintCreate
    from app.db.models import Organisation, OrganisationMembership, User
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Cmp Deny", slug=f"cmp-d-{unique_suffix}")
    admin = User(
        email=f"oa-d-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    maint = User(
        email=f"mc-d-{unique_suffix}@example.com",
        display_name="Maint",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, admin, maint])
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
                user_id=maint.id,
                organisation_id=org.id,
                role=HMoreRole.MAINTENANCE_CONTRACTOR,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()
    apply_organisation_rls(db_session, org.id)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    maint_ctx = _ctx(HMoreRole.MAINTENANCE_CONTRACTOR, org.id, maint.id)
    complaint_service.ensure_defaults(db_session, admin_ctx)
    row = complaint_service.create_complaint(
        db_session,
        admin_ctx,
        ComplaintCreate(title="X", description="Y"),
    )
    with pytest.raises(HTTPException) as denied:
        complaint_service.get_complaint(db_session, maint_ctx, row.id)
    assert denied.value.status_code == 403
