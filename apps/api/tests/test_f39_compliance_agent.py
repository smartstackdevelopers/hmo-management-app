"""F3.9 PostgreSQL tests. AI calls monkeypatched. Rules must not mutate source records."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.compliance_agent import service as compliance_service
from app.core.config import Settings
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.audit import AuditEvent
from app.db.models.compliance import StaffTrainingRecord
from app.db.models.enums import HMoreRole, MembershipStatus
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass
from sqlalchemy import select


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
    org = Organisation(name=f"CA {suffix}", slug=f"ca-{suffix}")
    other = Organisation(name=f"CB {suffix}", slug=f"cb-{suffix}")
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
    session.flush()
    return org, other, admin, worker


@pytest.mark.postgres
def test_f39_sweep_finds_expired_training_without_mutating_or_auto_resolving(
    db_session: Session, unique_suffix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    apply_platform_rls_bypass(db_session)
    org, other, admin, worker = _seed(db_session, unique_suffix)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, worker.id)
    apply_organisation_rls(db_session, org.id)

    training = StaffTrainingRecord(
        organisation_id=org.id,
        staff_user_id=worker.id,
        created_by_user_id=admin.id,
        title="First aid",
        category="health",
        completion_date=date.today() - timedelta(days=400),
        expiry_date=date.today() - timedelta(days=10),
        status="completed",
    )
    db_session.add(training)
    db_session.flush()
    original_expiry = training.expiry_date
    original_status = training.status

    def _budget(*_a, **_k):
        raise HTTPException(status_code=402, detail="AI usage limit reached")

    monkeypatch.setattr(compliance_service, "explain_findings", _budget)

    first = compliance_service.run_sweep(
        db_session,
        admin_ctx,
        modules=["training"],
        settings=_settings(ai_service_base_url="http://ai.test", ai_service_token="token"),
    )
    assert first["legal_certification"] is False
    assert first["autonomous_decision"] is False
    assert first["ai_status"] == "skipped_budget"
    assert first["findings_created"] >= 1
    assert any(item["rule_id"] == "training.expired" for item in first["findings"])
    assert "does not provide legal certification" in first["notice"]

    db_session.refresh(training)
    assert training.expiry_date == original_expiry
    assert training.status == original_status

    again = compliance_service.run_sweep(
        db_session,
        admin_ctx,
        modules=["training"],
        settings=_settings(),
    )
    assert again["findings_deduplicated"] >= 1

    finding_id = uuid.UUID(first["findings"][0]["id"])
    with pytest.raises(HTTPException) as denied:
        compliance_service.review_finding(
            db_session, worker_ctx, finding_id, decision="confirm", review_comment=None
        )
    assert denied.value.status_code == 403

    reviewed = compliance_service.review_finding(
        db_session, admin_ctx, finding_id, decision="confirm", review_comment="Checked"
    )
    assert reviewed["review_status"] == "confirmed"
    db_session.refresh(training)
    assert training.status == original_status

    resolved = compliance_service.resolve_finding(
        db_session, admin_ctx, finding_id, review_comment="Renewed offline", corrective_action_ref="training/renew"
    )
    assert resolved["resolution_status"] == "resolved"

    outsider = User(email=f"o-{unique_suffix}@example.com", display_name="O", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add(outsider)
    db_session.flush()
    with pytest.raises(HTTPException) as hidden:
        compliance_service.get_sweep(
            db_session, _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, outsider.id), uuid.UUID(first["id"])
        )
    assert hidden.value.status_code in {403, 404}

    actions = set(db_session.scalars(select(AuditEvent.action).where(AuditEvent.organisation_id == org.id)).all())
    assert audit_events.AI_COMPLIANCE_SWEEP_REQUESTED in actions
    assert audit_events.AI_COMPLIANCE_FINDINGS_GENERATED in actions
    assert audit_events.AI_COMPLIANCE_FINDING_RESOLVED in actions


@pytest.mark.postgres
def test_f39_unverifiable_module_is_not_a_confirmed_failure(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, admin, _worker = _seed(db_session, unique_suffix)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    apply_organisation_rls(db_session, org.id)
    result = compliance_service.run_sweep(
        db_session,
        admin_ctx,
        modules=["invented_module"],
        settings=_settings(),
    )
    assert any(item["result"] == "unable_to_verify" for item in result["findings"])
    assert all(item["result"] != "passed" for item in result["findings"])
