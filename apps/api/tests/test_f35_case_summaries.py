"""F3.5 PostgreSQL tests. AI provider calls are mocked. Heuristic path is not a real LLM."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.core.config import Settings
from app.db.models import Organisation, OrganisationMembership, Tenant, User
from app.db.models.audit import AuditEvent
from app.db.models.case_summaries import CaseSummary
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.support_ops import CaseAssignment, DailyLog
from app.case_summaries import service as case_service
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def _settings() -> Settings:
    return Settings(environment="test", ai_service_base_url="", ai_service_token="")


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
    org = Organisation(name=f"CS {suffix}", slug=f"cs-{suffix}")
    other = Organisation(name=f"CT {suffix}", slug=f"ct-{suffix}")
    admin = User(email=f"admin-{suffix}@example.com", display_name="Admin", external_subject=f"auth0|{uuid.uuid4()}")
    worker = User(email=f"sw-{suffix}@example.com", display_name="SW", external_subject=f"auth0|{uuid.uuid4()}")
    session.add_all([org, other, admin, worker])
    session.flush()
    tenant = Tenant(organisation_id=org.id, preferred_name=f"Tenant {suffix}", tenancy_reference=f"T-{suffix}")
    other_tenant = Tenant(organisation_id=other.id, preferred_name="Other", tenancy_reference=f"O-{suffix}")
    session.add_all([tenant, other_tenant])
    session.flush()
    session.add_all(
        [
            OrganisationMembership(
                user_id=admin.id, organisation_id=org.id, role=HMoreRole.ORGANISATION_ADMIN, status=MembershipStatus.ACTIVE
            ),
            OrganisationMembership(
                user_id=worker.id, organisation_id=org.id, role=HMoreRole.SUPPORT_WORKER, status=MembershipStatus.ACTIVE
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
        notes="Discussed warehouse work.",
        interaction_type="in_person",
        follow_up_required=False,
        next_action=None,
        status="active",
    )
    session.add(log)
    session.flush()
    return org, other, admin, worker, tenant, other_tenant, log


@pytest.mark.postgres
def test_f35_generate_review_version_and_audit(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, admin, _worker, tenant, _ot, log = _seed(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    settings = _settings()

    first = case_service.generate_summary(db_session, ctx, tenant_id=tenant.id, settings=settings)
    assert first["status"] == "pending_review"
    assert first["version_number"] == 1
    assert first["ai_generated"] is True
    assert first["generation_method"] == "structured_heuristic"
    assert first["idempotent"] is False
    assert first["stale"] is False
    assert any(ref["id"] == str(log.id) for ref in first["source_refs"])
    assert "Visit completed" in first["sections"]["recent_support"]

    second = case_service.generate_summary(db_session, ctx, tenant_id=tenant.id, settings=settings)
    assert second["idempotent"] is True
    assert second["id"] == first["id"]

    approved = case_service.review_summary(
        db_session, ctx, uuid.UUID(first["id"]), decision="approve", review_comment="Checked sources"
    )
    assert approved["status"] == "approved"
    assert approved["review_comment"] == "Checked sources"
    assert tenant.status.value == "active"

    with pytest.raises(HTTPException) as review_again:
        case_service.review_summary(
            db_session, ctx, uuid.UUID(first["id"]), decision="reject", review_comment=None
        )
    assert review_again.value.status_code == 409

    regenerated = case_service.regenerate_summary(db_session, ctx, uuid.UUID(first["id"]), settings=settings)
    assert regenerated["version_number"] == 2
    assert regenerated["regenerated"] is True
    assert regenerated["status"] == "pending_review"
    versions = case_service.list_versions(db_session, ctx, tenant.id, page=1, page_size=10)
    assert [item["version_number"] for item in versions["items"]] == [2, 1]

    log.summary = "Visit amended"
    db_session.flush()
    current = case_service.get_summary(db_session, ctx, uuid.UUID(first["id"]))
    assert current["stale"] is True

    actions = set(
        db_session.scalars(
            select(AuditEvent.action).where(AuditEvent.organisation_id == org.id, AuditEvent.resource_type.in_(["case_summary", "tenant"]))
        ).all()
    )
    assert audit_events.AI_CASE_SUMMARY_COMPLETED in actions
    assert audit_events.AI_CASE_SUMMARY_APPROVED in actions
    assert audit_events.AI_CASE_SUMMARY_REGENERATED in actions


@pytest.mark.postgres
def test_f35_invalid_ai_and_budget_and_provider(db_session: Session, unique_suffix: str, monkeypatch: pytest.MonkeyPatch) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, admin, _worker, tenant, _ot, _log = _seed(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    settings = Settings(environment="test", ai_service_base_url="http://ai.test", ai_service_token="token")

    def _invalid(*_args, **_kwargs):
        return {"request_id": "r1", "result": {"summary": {"sections": {}}, "prompt_id": "p", "prompt_version": "1"}}

    monkeypatch.setattr(case_service, "execute_case_summary", _invalid)
    with pytest.raises(HTTPException) as exc:
        case_service.generate_summary(db_session, ctx, tenant_id=tenant.id, settings=settings)
    assert exc.value.status_code == 422
    assert (
        db_session.scalar(
            select(func.count()).select_from(CaseSummary).where(CaseSummary.organisation_id == org.id)
        )
        == 0
    )

    def _budget(*_args, **_kwargs):
        raise HTTPException(status_code=402, detail={"error": "ai_budget_exceeded"})

    monkeypatch.setattr(case_service, "execute_case_summary", _budget)
    with pytest.raises(HTTPException) as exc:
        case_service.generate_summary(db_session, ctx, tenant_id=tenant.id, settings=settings)
    assert exc.value.status_code == 402

    def _down(*_args, **_kwargs):
        raise HTTPException(status_code=503, detail="AI service unreachable")

    monkeypatch.setattr(case_service, "execute_case_summary", _down)
    with pytest.raises(HTTPException) as exc:
        case_service.generate_summary(db_session, ctx, tenant_id=tenant.id, settings=settings)
    assert exc.value.status_code == 503
    assert (
        db_session.scalar(
            select(func.count()).select_from(CaseSummary).where(CaseSummary.organisation_id == org.id)
        )
        == 0
    )


@pytest.mark.postgres
def test_f35_rbac_and_isolation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, other, admin, worker, tenant, other_tenant, _log = _seed(db_session, unique_suffix)
    settings = _settings()
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    created = case_service.generate_summary(db_session, admin_ctx, tenant_id=tenant.id, settings=settings)

    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, worker.id)
    visible = case_service.get_summary(db_session, worker_ctx, uuid.UUID(created["id"]))
    assert visible["tenant_id"] == str(tenant.id)
    with pytest.raises(HTTPException) as exc:
        case_service.review_summary(db_session, worker_ctx, uuid.UUID(created["id"]), decision="reject", review_comment=None)
    assert exc.value.status_code == 403

    stranger = User(email=f"str-{unique_suffix}@example.com", display_name="Stranger", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add(stranger)
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=stranger.id, organisation_id=org.id, role=HMoreRole.SUPPORT_WORKER, status=MembershipStatus.ACTIVE
        )
    )
    db_session.flush()
    with pytest.raises(HTTPException) as exc:
        case_service.generate_summary(db_session, _ctx(HMoreRole.SUPPORT_WORKER, org.id, stranger.id), tenant_id=tenant.id, settings=settings)
    assert exc.value.status_code in {403, 404}

    with pytest.raises(HTTPException) as exc:
        case_service.generate_summary(db_session, admin_ctx, tenant_id=other_tenant.id, settings=settings)
    assert exc.value.status_code in {403, 404}

    other_admin = User(email=f"oa-{unique_suffix}@example.com", display_name="OA", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add(other_admin)
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=other_admin.id, organisation_id=other.id, role=HMoreRole.ORGANISATION_ADMIN, status=MembershipStatus.ACTIVE
        )
    )
    db_session.flush()
    with pytest.raises(HTTPException) as exc:
        case_service.get_summary(db_session, _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, other_admin.id), uuid.UUID(created["id"]))
    assert exc.value.status_code in {403, 404}

    apply_organisation_rls(db_session, other.id)
    assert list(db_session.scalars(select(CaseSummary)).all()) == []
    apply_organisation_rls(db_session, org.id)
    assert db_session.get(CaseSummary, uuid.UUID(created["id"])) is not None
