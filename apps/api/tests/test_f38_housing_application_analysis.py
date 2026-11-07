"""F3.8 PostgreSQL tests. AI calls are local or monkeypatched. No housing decisions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.core.config import Settings
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.audit import AuditEvent
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.db.models.housing import HousingApplication, WaitingListEntry
from app.db.models.support_ops import CaseAssignment
from app.db.models.tenant import Tenant
from app.evidence import service as evidence_service
from app.housing import service as housing_service
from app.housing.schemas import ApplicationCreate
from app.housing_application_analysis import service as analysis_service
from app.rbac.context import AuthorizationContext, MembershipView
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
    org = Organisation(name=f"HA {suffix}", slug=f"ha-{suffix}")
    other = Organisation(name=f"HB {suffix}", slug=f"hb-{suffix}")
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
        preferred_name="Applicant",
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
def test_f38_analysis_does_not_change_application_or_waiting_list(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, admin, worker, tenant = _seed(db_session, unique_suffix)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, worker.id)
    apply_organisation_rls(db_session, org.id)
    created = housing_service.create_application(
        db_session,
        admin_ctx,
        ApplicationCreate(
            tenant_id=tenant.id,
            housing_requirements="Need a single room near support services",
            household_summary=None,
            supporting_information=None,
            priority="normal",
        ),
    )
    app_id = uuid.UUID(created["id"])
    evidence_service.seed_checklist_from_templates(db_session, admin_ctx, app_id)
    app = db_session.get(HousingApplication, app_id)
    assert app is not None
    original_status = app.status
    settings = _settings()
    first = analysis_service.run_analysis(db_session, admin_ctx, application_id=app_id, settings=settings)
    assert first["housing_decision"] is False
    assert first["legal_certification"] is False
    assert "does not determine housing eligibility" in first["notice"]
    assert first["checklist_summary"]["missing"] >= 1 or first["checklist_summary"]["incomplete"] >= 1
    assert any(item["code"] == "checklist_not_configured" or item["source"] == "evidence" for item in first["findings"])
    db_session.refresh(app)
    assert app.status == original_status
    assert db_session.scalar(select(WaitingListEntry).where(WaitingListEntry.application_id == app_id)) is None

    again = analysis_service.run_analysis(db_session, admin_ctx, application_id=app_id, settings=settings)
    assert again["idempotent"] is True

    with pytest.raises(HTTPException) as denied:
        analysis_service.decide_finding(
            db_session, worker_ctx, uuid.UUID(first["findings"][0]["id"]), decision="confirm", review_comment=None
        )
    assert denied.value.status_code == 403

    reviewed = analysis_service.decide_finding(
        db_session,
        admin_ctx,
        uuid.UUID(first["findings"][0]["id"]),
        decision="confirm",
        review_comment="Seen",
    )
    assert any(item["review_status"] == "confirmed" for item in reviewed["findings"])
    db_session.refresh(app)
    assert app.status == original_status

    actions = set(db_session.scalars(select(AuditEvent.action).where(AuditEvent.organisation_id == org.id)).all())
    assert audit_events.AI_HOUSING_APPLICATION_REQUESTED in actions
    assert audit_events.AI_HOUSING_APPLICATION_CHECKLIST_COMPLETED in actions
    assert audit_events.HOUSING_APPLICATION_APPROVE not in actions
    assert audit_events.HOUSING_APPLICATION_REJECT not in actions


@pytest.mark.postgres
def test_f38_budget_cross_org_and_no_auto_reject(db_session: Session, unique_suffix: str, monkeypatch: pytest.MonkeyPatch) -> None:
    apply_platform_rls_bypass(db_session)
    org, other, admin, _worker, tenant = _seed(db_session, unique_suffix)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    apply_organisation_rls(db_session, org.id)
    created = housing_service.create_application(
        db_session,
        admin_ctx,
        ApplicationCreate(tenant_id=tenant.id, housing_requirements="Need housing", priority="normal"),
    )
    app_id = uuid.UUID(created["id"])
    app = db_session.get(HousingApplication, app_id)
    assert app is not None
    original_status = app.status

    def _budget(*_a, **_k):
        raise HTTPException(status_code=402, detail="AI usage limit reached")

    monkeypatch.setattr(analysis_service, "explain_gaps", _budget)
    capped = analysis_service.run_analysis(
        db_session,
        admin_ctx,
        application_id=app_id,
        force=True,
        settings=_settings(ai_service_base_url="http://ai.test", ai_service_token="token"),
    )
    assert capped["ai_status"] == "skipped_budget"
    assert capped["findings"]
    db_session.refresh(app)
    assert app.status == original_status

    outsider = User(email=f"o-{unique_suffix}@example.com", display_name="O", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add(outsider)
    db_session.flush()
    with pytest.raises(HTTPException) as hidden:
        analysis_service.get_analysis(
            db_session, _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, outsider.id), uuid.UUID(capped["id"])
        )
    assert hidden.value.status_code in {403, 404}
