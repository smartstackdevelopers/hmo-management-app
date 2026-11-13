"""F3.10 PostgreSQL tests. Approved content only; tenant isolation; pilot gate."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.communication import CommunicationAnnouncement
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.maintenance import MaintenanceEmergencyContent
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenant_assistant import service as ta_service
from app.tenant_assistant.content import invalidate_org_content_cache
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def _settings(org_id: uuid.UUID | None = None, **kwargs) -> Settings:
    base = dict(
        environment="test",
        ai_service_base_url="",
        ai_service_token="",
        tenant_assistant_pilot_organisation_ids=str(org_id) if org_id else "",
        tenant_assistant_hourly_limit=30,
    )
    base.update(kwargs)
    return Settings(**base)


def _ctx(role: HMoreRole, org_id: uuid.UUID, user_id: uuid.UUID) -> OrganisationContext:
    user = SimpleNamespace(
        id=user_id,
        authorization_version=1,
        external_subject=f"auth0|{uuid.uuid4()}",
        email="t@example.com",
        display_name="T",
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
    org = Organisation(name=f"TA {suffix}", slug=f"ta-{suffix}")
    other = Organisation(name=f"TB {suffix}", slug=f"tb-{suffix}")
    tenant_a = User(email=f"ta-{suffix}@example.com", display_name="TA", external_subject=f"auth0|{uuid.uuid4()}")
    tenant_b = User(email=f"tb-{suffix}@example.com", display_name="TB", external_subject=f"auth0|{uuid.uuid4()}")
    admin = User(email=f"adm-{suffix}@example.com", display_name="A", external_subject=f"auth0|{uuid.uuid4()}")
    session.add_all([org, other, tenant_a, tenant_b, admin])
    session.flush()
    session.add_all(
        [
            OrganisationMembership(
                user_id=tenant_a.id, organisation_id=org.id, role=HMoreRole.TENANT, status=MembershipStatus.ACTIVE
            ),
            OrganisationMembership(
                user_id=tenant_b.id, organisation_id=org.id, role=HMoreRole.TENANT, status=MembershipStatus.ACTIVE
            ),
            OrganisationMembership(
                user_id=admin.id,
                organisation_id=org.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    session.flush()
    return org, other, tenant_a, tenant_b, admin


@pytest.mark.postgres
def test_f310_answers_from_published_announcement_only(
    db_session: Session, unique_suffix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    apply_platform_rls_bypass(db_session)
    org, other, tenant_a, tenant_b, admin = _seed(db_session, unique_suffix)
    apply_organisation_rls(db_session, org.id)
    invalidate_org_content_cache(org.id)

    published = CommunicationAnnouncement(
        organisation_id=org.id,
        reference_number=f"ANN-{unique_suffix}-1",
        title="Rent payment office hours",
        body="The rent desk is open Monday to Friday 9am to 5pm for payment queries.",
        priority="normal",
        audience="tenants_only",
        channels={"in_app": True},
        status="published",
        published_at=datetime.now(timezone.utc),
        created_by_user_id=admin.id,
        published_by_user_id=admin.id,
    )
    draft = CommunicationAnnouncement(
        organisation_id=org.id,
        reference_number=f"ANN-{unique_suffix}-2",
        title="Secret draft rent policy",
        body="Draft internal rent increase details must never appear.",
        priority="normal",
        audience="tenants_only",
        channels={"in_app": True},
        status="draft",
        created_by_user_id=admin.id,
    )
    staff_only = CommunicationAnnouncement(
        organisation_id=org.id,
        reference_number=f"ANN-{unique_suffix}-3",
        title="Staff only briefing",
        body="Internal staff caseload notes.",
        priority="normal",
        audience="staff_only",
        channels={"in_app": True},
        status="published",
        published_at=datetime.now(timezone.utc),
        created_by_user_id=admin.id,
        published_by_user_id=admin.id,
    )
    unapproved_emergency = MaintenanceEmergencyContent(
        organisation_id=org.id,
        kind="gas",
        title="Unapproved gas text",
        body="Not approved for tenants",
        approved_for_use=False,
    )
    approved_emergency = MaintenanceEmergencyContent(
        organisation_id=org.id,
        kind="fire",
        title="Fire assembly point",
        body="Assemble at the car park if the fire alarm sounds.",
        approved_for_use=True,
    )
    db_session.add_all([published, draft, staff_only, unapproved_emergency, approved_emergency])
    db_session.flush()

    ctx_a = _ctx(HMoreRole.TENANT, org.id, tenant_a.id)
    settings = _settings(org.id)

    def _fake_ai(*_a, **_k):
        return {
            "result": {
                "answer": "Information only — rent desk hours are Monday to Friday 9am to 5pm from approved content.",
                "grounded": True,
                "prompt_id": "hmore.tenant_assistant.v1",
                "prompt_version": "1.0.0",
                "cache_status": "miss",
            }
        }

    monkeypatch.setattr(ta_service, "ask_grounded", _fake_ai)

    result = ta_service.ask(db_session, ctx_a, question="What are the rent payment office hours?", settings=settings)
    assert result["makes_official_decisions"] is False
    assert "9am" in result["message"]["body"]
    assert any(ref["content_id"] == str(published.id) for ref in result["message"]["source_refs"])
    assert all(ref["content_id"] != str(draft.id) for ref in result["message"]["source_refs"])
    assert all(ref["content_id"] != str(staff_only.id) for ref in result["message"]["source_refs"])

    # Monkeypatch would invent an answer if retrieval were too loose; require no-content path.
    no_match = ta_service.ask(
        db_session, ctx_a, question="What is the secret intergalactic policy code?", settings=settings
    )
    assert no_match["message"]["ai_status"] == "no_content"
    assert "cannot confirm" in no_match["message"]["body"].lower()
    assert no_match["message"]["source_refs"] == []

    # Tenant B cannot read Tenant A's conversation
    ctx_b = _ctx(HMoreRole.TENANT, org.id, tenant_b.id)
    with pytest.raises(HTTPException) as hidden:
        ta_service.get_conversation(db_session, ctx_b, uuid.UUID(result["conversation_id"]))
    assert hidden.value.status_code == 403

    # Cross-org pilot denial
    outsider = User(email=f"o-{unique_suffix}@example.com", display_name="O", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add(outsider)
    db_session.flush()
    with pytest.raises(HTTPException) as denied:
        ta_service.ask(
            db_session,
            _ctx(HMoreRole.TENANT, other.id, outsider.id),
            question="What are rent hours?",
            settings=_settings(org.id),
        )
    assert denied.value.status_code == 403

    # Admin cannot ask as tenant assistant
    with pytest.raises(HTTPException) as staff_denied:
        ta_service.ask(
            db_session,
            _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id),
            question="What are rent hours?",
            settings=settings,
        )
    assert staff_denied.value.status_code == 403

    # Escalation: housing decision
    housing = ta_service.ask(
        db_session, ctx_a, question="Am I eligible for housing approval?", settings=settings
    )
    assert housing["message"]["escalation"] == "housing_decision"
    assert "cannot decide housing" in housing["message"]["body"].lower()


@pytest.mark.postgres
def test_f310_disabled_when_pilot_env_empty(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, tenant_a, _tenant_b, _admin = _seed(db_session, unique_suffix)
    # F3.15: empty env alone no longer disables when DB flags are enabled.
    # Explicitly disable the Tenant Assistant flag to assert the gate.
    from app.ai_feature_flags.service import update_feature
    from app.ai_usage.features import FEATURE_TENANT_ASSISTANT

    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, _admin.id)
    update_feature(
        db_session,
        admin_ctx,
        FEATURE_TENANT_ASSISTANT,
        enabled=False,
        pilot_enabled=False,
        change_reason="test disable TA",
    )
    apply_organisation_rls(db_session, org.id)
    avail = ta_service.availability(_ctx(HMoreRole.TENANT, org.id, tenant_a.id), _settings(None))
    # availability() still reflects env allowlist for display; ask is DB-gated.
    with pytest.raises(HTTPException) as exc:
        ta_service.ask(
            db_session,
            _ctx(HMoreRole.TENANT, org.id, tenant_a.id),
            question="Hello there office hours?",
            settings=_settings(None),
        )
    assert exc.value.status_code == 403
    _ = avail

