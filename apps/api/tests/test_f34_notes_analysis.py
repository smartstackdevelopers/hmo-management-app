"""F3.4 PostgreSQL tests — analysis, review, isolation, duplicate prevention."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Organisation, OrganisationMembership, Tenant, User
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.notes_analysis import DailyLogAiAnalysis, DailyLogAiSuggestion
from app.db.models.support_ops import CaseAssignment, DailyLog
from app.notes_analysis import service as na_service
from app.rbac.context import AuthorizationContext, MembershipView
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


def _seed(session: Session, suffix: str):
    org = Organisation(name=f"NA {suffix}", slug=f"na-{suffix}")
    other = Organisation(name=f"NB {suffix}", slug=f"nb-{suffix}")
    admin = User(
        email=f"admin-{suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    worker = User(
        email=f"sw-{suffix}@example.com",
        display_name="SW",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    session.add_all([org, other, admin, worker])
    session.flush()
    tenant = Tenant(
        organisation_id=org.id,
        preferred_name=f"Tenant {suffix}",
        tenancy_reference=f"T-{suffix}",
    )
    session.add(tenant)
    session.flush()
    session.add_all(
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
    session.flush()
    log = DailyLog(
        organisation_id=org.id,
        tenant_id=tenant.id,
        author_user_id=worker.id,
        log_date=date.today(),
        logged_at=datetime.now(timezone.utc),
        activity_category="support",
        summary="Visit completed",
        notes="Discussed warehouse work. Meeting planned. Follow up needed.",
        interaction_type="in_person",
        follow_up_required=True,
        next_action=None,
        status="active",
    )
    session.add(log)
    session.flush()
    return org, other, admin, worker, tenant, log


@pytest.mark.postgres
def test_f34_analyse_and_review(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, admin, _worker, _tenant, log = _seed(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)

    first = na_service.run_analysis(db_session, ctx, daily_log_id=log.id)
    assert first["ai_generated"] is True
    assert first["status"] == "pending_review"
    assert first["idempotent"] is False
    assert "AI-generated" in (first["summary"] or "")

    second = na_service.run_analysis(db_session, ctx, daily_log_id=log.id)
    assert second["idempotent"] is True
    assert second["id"] == first["id"]

    suggestions = first["suggestions"]
    assert suggestions
    pending = [s for s in suggestions if s["review_status"] == "pending"]
    assert pending
    decided = na_service.decide_suggestion(
        db_session,
        ctx,
        uuid.UUID(pending[0]["id"]),
        decision="approve",
        reviewer_note="Looks reasonable",
    )
    assert decided["review_status"] == "approved"

    reviewed = na_service.review_analysis(
        db_session, ctx, uuid.UUID(first["id"]), decision="partially_approve"
    )
    assert reviewed["status"] == "partially_approved"


@pytest.mark.postgres
def test_f34_stale_suggestion_blocked(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, _o, admin, _w, _t, log = _seed(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    out = na_service.run_analysis(db_session, ctx, daily_log_id=log.id)
    sug_id = uuid.UUID(out["suggestions"][0]["id"])
    log.notes = "Changed content after analysis"
    db_session.flush()
    with pytest.raises(HTTPException) as exc:
        na_service.decide_suggestion(db_session, ctx, sug_id, decision="approve")
    assert exc.value.status_code == 409


@pytest.mark.postgres
def test_f34_cross_org_isolation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, other, admin, _w, _t, log = _seed(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    out = na_service.run_analysis(db_session, ctx, daily_log_id=log.id)
    analysis_id = uuid.UUID(out["id"])

    apply_organisation_rls(db_session, other.id)
    rows = list(db_session.scalars(select(DailyLogAiAnalysis)).all())
    assert rows == []
    sug = list(db_session.scalars(select(DailyLogAiSuggestion)).all())
    assert sug == []

    apply_organisation_rls(db_session, org.id)
    found = db_session.get(DailyLogAiAnalysis, analysis_id)
    assert found is not None


@pytest.mark.postgres
def test_f34_unassigned_worker_denied(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, _o, _admin, _worker, _t, log = _seed(db_session, unique_suffix)
    stranger = User(
        email=f"str-{unique_suffix}@example.com",
        display_name="Stranger",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add(stranger)
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=stranger.id,
            organisation_id=org.id,
            role=HMoreRole.SUPPORT_WORKER,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, stranger.id)
    with pytest.raises(HTTPException) as exc:
        na_service.run_analysis(db_session, ctx, daily_log_id=log.id)
    assert exc.value.status_code in {403, 404}

