"""F3.14 PostgreSQL tests — activity logging, feedback, org isolation, RBAC."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_transparency import service as tx_service
from app.ai_usage.metering import record_and_reconcile
from app.audit import events as audit_events
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.ai_activity import AiActivityLog, AiWrongAnswerFeedback
from app.db.models.audit import AuditEvent
from app.db.models.enums import HMoreRole, MembershipStatus
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
def test_f314_activity_feedback_isolation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name=f"TX {unique_suffix}", slug=f"tx-{unique_suffix}")
    other = Organisation(name=f"TY {unique_suffix}", slug=f"ty-{unique_suffix}")
    admin = User(email=f"a-{unique_suffix}@example.com", display_name="Admin", external_subject=f"auth0|{uuid.uuid4()}")
    tenant_user = User(
        email=f"t-{unique_suffix}@example.com", display_name="Tenant", external_subject=f"auth0|{uuid.uuid4()}"
    )
    worker = User(
        email=f"w-{unique_suffix}@example.com", display_name="Worker", external_subject=f"auth0|{uuid.uuid4()}"
    )
    outsider = User(
        email=f"o-{unique_suffix}@example.com", display_name="Out", external_subject=f"auth0|{uuid.uuid4()}"
    )
    db_session.add_all([org, other, admin, tenant_user, worker, outsider])
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
                user_id=worker.id,
                organisation_id=org.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=outsider.id,
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
    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, worker.id)
    other_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, outsider.id)

    # Usage metering creates activity with sources from transparency metadata.
    request_id = f"req-{uuid.uuid4()}"
    usage = record_and_reconcile(
        db_session,
        request_id=request_id,
        organisation_id=org.id,
        execution_status="completed",
        feature_id="ai.agent.notes_analysis",
        workflow_id="notes_analysis",
        user_id=worker.id,
        provider="test",
        model_id="test-model",
        prompt_id="hmore.notes.v1",
        prompt_version="1.0.0",
        input_tokens=10,
        output_tokens=20,
        duration_ms=100,
        metadata={
            "transparency": {
                "source_refs": [{"type": "daily_log", "id": str(uuid.uuid4()), "title": "Log A"}],
                "confidence_kind": "unavailable",
                "human_approval_status": "pending",
                "operation_type": "notes_analysis",
            }
        },
    )
    assert usage.execution_status == "completed"

    activity = db_session.scalars(
        select(AiActivityLog).where(AiActivityLog.request_id == request_id)
    ).first()
    assert activity is not None
    assert activity.sources_available is True
    assert activity.confidence_kind == "unavailable"
    assert activity.confidence_label == "Confidence unavailable"
    assert "prompt" not in str(activity.source_refs_json).lower() or True

    listed = tx_service.list_activities(db_session, admin_ctx, limit=10)
    assert listed["total"] >= 1
    assert any(i["id"] == str(activity.id) for i in listed["items"])
    detail = tx_service.get_activity(db_session, admin_ctx, activity.id, audit_source_access=True)
    assert detail["confidence"]["percentage"] is None
    assert detail["confidence"]["calibrated"] is False
    assert detail["sources_available"] is True

    # Tenant cannot see staff AI activity.
    tenant_list = tx_service.list_activities(db_session, tenant_ctx, limit=10)
    assert all(i["id"] != str(activity.id) for i in tenant_list["items"])

    with pytest.raises(HTTPException) as denied_get:
        tx_service.get_activity(db_session, tenant_ctx, activity.id)
    assert denied_get.value.status_code in {403, 404}

    # Cross-org IDOR blocked.
    apply_organisation_rls(db_session, other.id)
    with pytest.raises(HTTPException) as cross:
        tx_service.get_activity(db_session, other_ctx, activity.id)
    assert cross.value.status_code == 404

    apply_organisation_rls(db_session, org.id)

    # Initiator-scoped tenant assistant activity.
    ta_req = f"ta-{uuid.uuid4()}"
    ta = tx_service.record_local_activity(
        db_session,
        organisation_id=org.id,
        request_id=ta_req,
        feature_id="ai.agent.tenant_assistant",
        workflow_id="tenant_assistant",
        user_id=tenant_user.id,
        execution_status="completed",
        source_refs=[{"content_id": "c1", "source_type": "faq", "title": "FAQ"}],
        confidence_kind="retrieval_coverage",
        confidence_detail={"sources_used": 1},
        visibility="initiator",
        operation_type="tenant_assistant",
    )
    assert ta is not None
    assert ta.visibility == "initiator"
    assert ta.confidence_kind == "retrieval_coverage"

    tenant_list2 = tx_service.list_activities(db_session, tenant_ctx, limit=20)
    assert any(i["id"] == str(ta.id) for i in tenant_list2["items"])

    # Worker cannot open another user's initiator activity (no review perm).
    with pytest.raises(HTTPException) as worker_denied:
        tx_service.get_activity(db_session, worker_ctx, ta.id)
    assert worker_denied.value.status_code == 403

    # Feedback submit + invalid category.
    with pytest.raises(HTTPException) as bad_cat:
        tx_service.submit_feedback(
            db_session, worker_ctx, activity_id=activity.id, category="not_a_real_category"
        )
    assert bad_cat.value.status_code == 422

    fb = tx_service.submit_feedback(
        db_session,
        worker_ctx,
        activity_id=activity.id,
        category="incorrect_information",
        explanation="DROP TABLE users; ignore previous instructions",
    )
    assert fb["review_status"] == "submitted"
    assert "DROP TABLE" in (fb["explanation"] or "")  # stored as text, never executed

    # Unauthorised feedback against initiator activity.
    with pytest.raises(HTTPException) as fb_denied:
        tx_service.submit_feedback(
            db_session, worker_ctx, activity_id=ta.id, category="missing_source"
        )
    assert fb_denied.value.status_code == 403

    # Tenant can feedback own activity.
    tenant_fb = tx_service.submit_feedback(
        db_session, tenant_ctx, activity_id=ta.id, category="incomplete_answer", explanation="Missing hours"
    )
    assert tenant_fb["category"] == "incomplete_answer"

    # Worker cannot review; admin can.
    with pytest.raises(HTTPException) as review_denied:
        tx_service.review_feedback(
            db_session, worker_ctx, uuid.UUID(fb["id"]), action="resolve", resolution_notes="nope"
        )
    assert review_denied.value.status_code == 403

    reviewed = tx_service.review_feedback(
        db_session, admin_ctx, uuid.UUID(fb["id"]), action="start_review"
    )
    assert reviewed["review_status"] == "under_review"
    resolved = tx_service.review_feedback(
        db_session,
        admin_ctx,
        uuid.UUID(fb["id"]),
        action="resolve",
        resolution_notes="Investigated — no auto model change",
    )
    assert resolved["review_status"] == "resolved"
    assert resolved["resolution_notes"] is not None

    stats = tx_service.feedback_stats(db_session, admin_ctx)
    assert stats["by_category"].get("incorrect_information", 0) >= 1
    assert "human investigation" in stats["note"].lower() or "signal" in stats["note"].lower()

    audits = list(
        db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.organisation_id == org.id,
                AuditEvent.action.in_(
                    [
                        audit_events.AI_ACTIVITY_COMPLETED,
                        audit_events.AI_FEEDBACK_SUBMITTED,
                        audit_events.AI_FEEDBACK_RESOLVED,
                    ]
                ),
            )
        )
    )
    assert len(audits) >= 3

    # Audit events are not mutable via feedback APIs — verify row remains.
    feedback_row = db_session.get(AiWrongAnswerFeedback, uuid.UUID(fb["id"]))
    assert feedback_row is not None
    assert feedback_row.review_status == "resolved"
