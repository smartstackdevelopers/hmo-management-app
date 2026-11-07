"""F3.7 PostgreSQL tests. Draft AI calls are local or monkeypatched."""

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
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.audit import AuditEvent
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.db.models.support_ops import CaseAssignment, DailyLog
from app.db.models.support_plans import SupportPlanGoal, TenantSupportPlan
from app.db.models.tenant import Tenant
from app.rbac.context import AuthorizationContext, MembershipView
from app.support_plan_drafts import service as draft_service
from app.support_plans.schemas import SupportPlanCreate
from app.support_plans import service as plan_service
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def _settings(**kwargs) -> Settings:
    base = dict(environment="test", ai_service_base_url="", ai_service_token="")
    base.update(kwargs)
    return Settings(**base)


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
    return OrganisationContext(user=user, organisation_id=org_id, role=role, authorization=authz)  # type: ignore[arg-type]


def _seed(session: Session, suffix: str):
    org = Organisation(name=f"SP {suffix}", slug=f"sp-{suffix}")
    other = Organisation(name=f"SQ {suffix}", slug=f"sq-{suffix}")
    admin = User(email=f"a-{suffix}@example.com", display_name="Admin", external_subject=f"auth0|{uuid.uuid4()}")
    worker = User(email=f"w-{suffix}@example.com", display_name="SW", external_subject=f"auth0|{uuid.uuid4()}")
    session.add_all([org, other, admin, worker])
    session.flush()
    session.add_all(
        [
            OrganisationMembership(
                user_id=admin.id, organisation_id=org.id, role=HMoreRole.ORGANISATION_ADMIN, status=MembershipStatus.ACTIVE
            ),
            OrganisationMembership(
                user_id=worker.id, organisation_id=org.id, role=HMoreRole.SUPPORT_WORKER, status=MembershipStatus.ACTIVE
            ),
        ]
    )
    tenant = Tenant(
        organisation_id=org.id,
        preferred_name="Ali",
        tenancy_reference=f"T-{suffix}",
        needs_goals="Help with weekly budgeting",
        status=RecordStatus.ACTIVE,
    )
    session.add(tenant)
    session.flush()
    session.add(
        CaseAssignment(
            organisation_id=org.id,
            tenant_id=tenant.id,
            support_worker_user_id=worker.id,
            assigned_by_user_id=admin.id,
            status="active",
            assigned_at=datetime.now(timezone.utc),
        )
    )
    session.flush()
    return org, other, admin, worker, tenant


@pytest.mark.postgres
def test_f37_draft_review_apply_does_not_skip_approval(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, admin, worker, tenant = _seed(db_session, unique_suffix)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, worker.id)
    apply_organisation_rls(db_session, org.id)
    plan = plan_service.create_plan(
        db_session,
        admin_ctx,
        SupportPlanCreate(
            tenant_id=tenant.id,
            title="Current plan",
            responsible_worker_user_id=worker.id,
            support_objectives="Recorded objective",
        ),
    )
    plan_id = uuid.UUID(plan["id"])
    stored = db_session.get(TenantSupportPlan, plan_id)
    assert stored is not None
    original_status = stored.status
    settings = _settings()
    created = draft_service.generate_draft(
        db_session, admin_ctx, tenant_id=tenant.id, plan_id=plan_id, settings=settings
    )
    assert created["status"] == "draft"
    assert created["is_operational_plan"] is False
    assert created["ai_generated"] is True
    assert created["content"]["suggested_goals"]
    db_session.refresh(stored)
    assert stored.status == original_status
    assert db_session.scalar(select(func.count()).select_from(SupportPlanGoal).where(SupportPlanGoal.plan_id == plan_id)) == 0

    again = draft_service.generate_draft(
        db_session, admin_ctx, tenant_id=tenant.id, plan_id=plan_id, settings=settings
    )
    assert again["idempotent"] is True

    with pytest.raises(HTTPException) as denied:
        draft_service.decide_draft(db_session, worker_ctx, uuid.UUID(created["id"]), decision="approve", review_comment=None)
    assert denied.value.status_code == 403
    with pytest.raises(HTTPException) as early:
        draft_service.apply_draft(db_session, admin_ctx, uuid.UUID(created["id"]))
    assert early.value.status_code == 409

    edited = draft_service.edit_draft(db_session, worker_ctx, uuid.UUID(created["id"]), created["content"])
    assert edited["human_edited"] is True
    assert edited["status"] == "draft"
    submitted = draft_service.submit_draft(db_session, worker_ctx, uuid.UUID(created["id"]))
    assert submitted["status"] == "pending_review"
    approved = draft_service.decide_draft(
        db_session, admin_ctx, uuid.UUID(created["id"]), decision="approve", review_comment="Checked sources"
    )
    assert approved["status"] == "approved"
    db_session.refresh(stored)
    assert stored.status == original_status

    applied = draft_service.apply_draft(db_session, worker_ctx, uuid.UUID(created["id"]))
    assert applied["status"] == "applied"
    assert applied["application"]["plan_status_unchanged"] == original_status
    assert len(applied["application"]["goal_ids"]) == 1
    db_session.refresh(stored)
    assert stored.status == original_status
    with pytest.raises(HTTPException) as duplicate:
        draft_service.apply_draft(db_session, worker_ctx, uuid.UUID(created["id"]))
    assert duplicate.value.status_code == 409

    actions = set(db_session.scalars(select(AuditEvent.action).where(AuditEvent.organisation_id == org.id)).all())
    assert audit_events.AI_SUPPORT_PLAN_DRAFT_REQUESTED in actions
    assert audit_events.AI_SUPPORT_PLAN_DRAFT_APPROVED in actions
    assert audit_events.AI_SUPPORT_PLAN_DRAFT_APPLIED in actions


@pytest.mark.postgres
def test_f37_reject_cap_conflict_and_cross_org(db_session: Session, unique_suffix: str, monkeypatch: pytest.MonkeyPatch) -> None:
    apply_platform_rls_bypass(db_session)
    org, other, admin, worker, tenant = _seed(db_session, unique_suffix)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    apply_organisation_rls(db_session, org.id)
    plan = plan_service.create_plan(
        db_session,
        admin_ctx,
        SupportPlanCreate(tenant_id=tenant.id, title="Plan", responsible_worker_user_id=worker.id),
    )
    plan_id = uuid.UUID(plan["id"])
    first = draft_service.generate_draft(db_session, admin_ctx, tenant_id=tenant.id, plan_id=plan_id, settings=_settings())
    draft_service.submit_draft(db_session, admin_ctx, uuid.UUID(first["id"]))
    rejected = draft_service.decide_draft(
        db_session, admin_ctx, uuid.UUID(first["id"]), decision="reject", review_comment="Not enough"
    )
    assert rejected["status"] == "rejected"
    assert db_session.scalar(select(func.count()).select_from(SupportPlanGoal).where(SupportPlanGoal.plan_id == plan_id)) == 0

    def _budget(*_a, **_k):
        raise HTTPException(status_code=402, detail="AI usage limit reached")

    monkeypatch.setattr(draft_service, "execute_support_plan_draft", _budget)
    with pytest.raises(HTTPException) as capped:
        draft_service.generate_draft(
            db_session,
            admin_ctx,
            tenant_id=tenant.id,
            plan_id=plan_id,
            force=True,
            settings=_settings(ai_service_base_url="http://ai.test", ai_service_token="token"),
        )
    assert capped.value.status_code == 402

    fresh = draft_service.generate_draft(
        db_session, admin_ctx, tenant_id=tenant.id, plan_id=plan_id, force=True, settings=_settings()
    )
    draft_service.submit_draft(db_session, admin_ctx, uuid.UUID(fresh["id"]))
    draft_service.decide_draft(db_session, admin_ctx, uuid.UUID(fresh["id"]), decision="approve", review_comment=None)
    db_session.add(
        DailyLog(
            organisation_id=org.id,
            tenant_id=tenant.id,
            author_user_id=worker.id,
            log_date=date.today(),
            logged_at=datetime.now(timezone.utc),
            activity_category="support",
            summary="Later note",
            notes="A note recorded after the draft.",
            status="active",
        )
    )
    db_session.flush()
    with pytest.raises(HTTPException) as stale:
        draft_service.apply_draft(db_session, admin_ctx, uuid.UUID(fresh["id"]))
    assert stale.value.status_code == 409

    outsider = User(email=f"o-{unique_suffix}@example.com", display_name="O", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add(outsider)
    db_session.flush()
    with pytest.raises(HTTPException) as hidden:
        draft_service.get_draft(db_session, _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, outsider.id), uuid.UUID(first["id"]))
    assert hidden.value.status_code in {403, 404}
