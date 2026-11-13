"""F2.9 tenant timeline, meetings, appointments, follow-ups (PostgreSQL integration)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.audit import events as audit_events
from app.db.models import AuditEvent, Organisation, OrganisationMembership, Tenant, User
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.db.models.support_ops import CaseAssignment
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.support.schemas import DailyLogCreate
from app.support import service as support_service
from app.tenant_timeline.schemas import MeetingCreate, TenantFollowUpCreate
from app.tenant_timeline import service as tl_service
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def test_f29_matrix_includes_timeline() -> None:
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.TIMELINE_READ)
    assert role_has_permission(HMoreRole.TENANT, Permission.TIMELINE_READ_OWN)
    assert not role_has_permission(HMoreRole.MAINTENANCE_CONTRACTOR, Permission.TIMELINE_READ)


def test_unauthenticated_timeline_401() -> None:
    client = TestClient(app)
    tid = str(uuid.uuid4())
    assert client.get(f"/api/v1/tenants/{tid}/timeline").status_code == 401


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
def test_timeline_and_meetings_isolation(db_session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="TL A", slug=f"tl-a-{unique_suffix}")
    org_b = Organisation(name="TL B", slug=f"tl-b-{unique_suffix}")
    db_session.add_all([org_a, org_b])
    db_session.flush()

    admin_a = User(
        email=f"oa-f29-{unique_suffix}@example.com",
        display_name="Admin A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    admin_b = User(
        email=f"ob-f29-{unique_suffix}@example.com",
        display_name="Admin B",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    sw = User(
        email=f"sw-f29-{unique_suffix}@example.com",
        display_name="SW",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    other_sw = User(
        email=f"sw2-f29-{unique_suffix}@example.com",
        display_name="SW2",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([admin_a, admin_b, sw, other_sw])
    db_session.flush()

    tenant = Tenant(
        organisation_id=org_a.id,
        preferred_name="Pat",
        status=RecordStatus.ACTIVE,
        user_id=None,
    )
    db_session.add(tenant)
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
                user_id=admin_b.id,
                organisation_id=org_b.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=sw.id,
                organisation_id=org_a.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=other_sw.id,
                organisation_id=org_a.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()

    now = datetime.now(timezone.utc)
    db_session.add(
        CaseAssignment(
            organisation_id=org_a.id,
            tenant_id=tenant.id,
            support_worker_user_id=sw.id,
            assigned_by_user_id=admin_a.id,
            status="active",
            assigned_at=now,
        )
    )
    db_session.flush()

    ctx_sw = _ctx(HMoreRole.SUPPORT_WORKER, org_a.id, sw.id)
    apply_organisation_rls(db_session, org_a.id)

    support_service.create_daily_log(
        db_session,
        ctx_sw,
        DailyLogCreate(
            tenant_id=tenant.id,
            activity_category="keywork",
            summary="Visit notes",
            notes="Detailed notes for timeline test.",
        ),
    )
    db_session.flush()

    page = tl_service.get_tenant_timeline(
        db_session,
        ctx_sw,
        tenant.id,
        page=1,
        page_size=20,
        sort="newest",
        activity_types=["daily_log"],
        date_from=None,
        date_to=None,
        assigned_user_id=None,
        search=None,
    )
    assert page["total"] >= 1
    types = {i["activity_type"] for i in page["items"]}
    assert "daily_log" in types

    ctx_other = _ctx(HMoreRole.SUPPORT_WORKER, org_a.id, other_sw.id)
    with pytest.raises(HTTPException) as exc:
        tl_service.get_tenant_timeline(
            db_session,
            ctx_other,
            tenant.id,
            page=1,
            page_size=20,
            sort="newest",
            activity_types=None,
            date_from=None,
            date_to=None,
            assigned_user_id=None,
            search=None,
        )
    assert exc.value.status_code == 403

    meeting = tl_service.create_meeting(
        db_session,
        ctx_sw,
        tenant.id,
        MeetingCreate(
            title="Review",
            purpose="Monthly",
            scheduled_at=now,
            status="scheduled",
        ),
    )
    assert meeting["reference_number"].startswith("TM-")

    ctx_oa = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin_a.id)
    fu = tl_service.create_follow_up(
        db_session,
        ctx_oa,
        tenant.id,
        TenantFollowUpCreate(
            action_description="Call housing",
            assigned_user_id=sw.id,
            due_at=now,
        ),
    )
    with pytest.raises(HTTPException) as exc:
        from app.tenant_timeline.schemas import TenantFollowUpUpdate

        tl_service.update_follow_up(
            db_session,
            ctx_other,
            tenant.id,
            uuid.UUID(fu["id"]),
            TenantFollowUpUpdate(status="in_progress"),
        )
    assert exc.value.status_code == 403

    apply_organisation_rls(db_session, org_b.id)
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, admin_b.id)
    with pytest.raises(HTTPException) as exc:
        tl_service.get_tenant_timeline(
            db_session,
            ctx_b,
            tenant.id,
            page=1,
            page_size=20,
            sort="newest",
            activity_types=None,
            date_from=None,
            date_to=None,
            assigned_user_id=None,
            search=None,
        )
    assert exc.value.status_code in {403, 404}

    apply_organisation_rls(db_session, org_a.id)
    audits = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.organisation_id == org_a.id,
            AuditEvent.action.in_(
                [
                    audit_events.TENANT_TIMELINE_READ,
                    audit_events.TENANT_MEETING_CREATE,
                    audit_events.TENANT_FOLLOW_UP_CREATE,
                ]
            ),
        )
    ).all()
    assert len(audits) >= 1

