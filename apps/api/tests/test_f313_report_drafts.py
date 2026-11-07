"""F3.13 PostgreSQL tests. AI unconfigured; reminders use ReminderRecord idempotency."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.core.config import Settings
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.audit import AuditEvent
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.scheduling import OperationalTask, ReminderRecord
from app.report_drafts import service as draft_service
from app.report_drafts.overdue import scan_organisation
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def _ctx(role: HMoreRole, org_id: uuid.UUID, user_id: uuid.UUID) -> OrganisationContext:
    user = SimpleNamespace(id=user_id, authorization_version=1, email="u@example.com", display_name="U")
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
    return OrganisationContext(user=user, organisation_id=org_id, role=role, authorization=authz)  # type: ignore[arg-type]


@pytest.mark.postgres
def test_f313_report_draft_and_overdue_dedupe(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name=f"RD {unique_suffix}", slug=f"rd-{unique_suffix}")
    other = Organisation(name=f"RX {unique_suffix}", slug=f"rx-{unique_suffix}")
    admin = User(email=f"a-{unique_suffix}@example.com", display_name="Admin", external_subject=f"auth0|{uuid.uuid4()}")
    worker = User(email=f"w-{unique_suffix}@example.com", display_name="SW", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add_all([org, other, admin, worker])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=admin.id,
            organisation_id=org.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    apply_organisation_rls(db_session, org.id)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    settings = Settings(ai_service_base_url="", ai_service_token="")

    draft = draft_service.generate_draft(
        db_session, admin_ctx, period_type="weekly", settings=settings
    )
    assert draft["status"] == "draft"
    assert draft["distributed"] is False
    assert draft["auto_approved"] is False
    assert "REQUIRES HUMAN REVIEW" in draft["ai_notice"]
    assert draft["metrics"]["metric_source"] == "f2.14_reporting_summaries"
    assert draft["ai_status"] == "skipped"

    again = draft_service.generate_draft(
        db_session, admin_ctx, period_type="weekly", settings=settings
    )
    assert again["id"] == draft["id"]

    edited = draft_service.edit_draft(
        db_session, admin_ctx, uuid.UUID(draft["id"]), edited_body="Reviewed narrative"
    )
    assert edited["edited_body"] == "Reviewed narrative"
    approved = draft_service.review_draft(
        db_session, admin_ctx, uuid.UUID(draft["id"]), decision="approve", review_comment="OK"
    )
    assert approved["status"] == "approved"
    assert approved["distributed"] is False

    with pytest.raises(HTTPException) as denied:
        draft_service.generate_draft(
            db_session, _ctx(HMoreRole.TENANT, org.id, worker.id), period_type="weekly", settings=settings
        )
    assert denied.value.status_code == 403

    due = datetime.now(timezone.utc) - timedelta(hours=2)
    task = OperationalTask(
        organisation_id=org.id,
        title="Overdue task",
        assigned_user_id=worker.id,
        created_by_user_id=admin.id,
        status="open",
        due_at=due,
    )
    db_session.add(task)
    db_session.flush()
    apply_platform_rls_bypass(db_session)
    first = scan_organisation(db_session, org.id)
    assert first["detected"] >= 1
    assert first["scheduled"] >= 1
    second = scan_organisation(db_session, org.id)
    assert second["deduped"] >= 1
    reminders = list(
        db_session.scalars(
            select(ReminderRecord).where(
                ReminderRecord.organisation_id == org.id,
                ReminderRecord.resource_id == task.id,
                ReminderRecord.reminder_kind == "task_overdue",
            )
        )
    )
    assert len(reminders) == 1

    outsider = User(
        email=f"o-{unique_suffix}@example.com",
        display_name="O",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add(outsider)
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=outsider.id,
            organisation_id=other.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    with pytest.raises(HTTPException) as hidden:
        draft_service.get_draft(
            db_session, _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, outsider.id), uuid.UUID(draft["id"])
        )
    assert hidden.value.status_code in {403, 404}

    actions = set(
        db_session.scalars(select(AuditEvent.action).where(AuditEvent.organisation_id == org.id)).all()
    )
    assert audit_events.REPORT_DRAFT_GENERATED in actions
    assert audit_events.REPORT_DRAFT_APPROVED in actions
    assert audit_events.OVERDUE_REMINDER_SCHEDULED in actions
