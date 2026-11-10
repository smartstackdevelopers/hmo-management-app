"""F3.15 PostgreSQL tests — flags, isolation, enforcement, audit."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_feature_flags import service as ff_service
from app.ai_feature_flags.cache import cache_clear_all, cache_get
from app.ai_usage.features import FEATURE_NOTES_ANALYSIS, FEATURE_TENANT_ASSISTANT
from app.audit import events as audit_events
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.audit import AuditEvent
from app.db.models.enums import HMoreRole, MembershipStatus
from app.notes_analysis import service as notes_service
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
@pytest.mark.no_ai_feature_flag_auto_enable
def test_f315_flags_isolation_and_enforcement(db_session: Session, unique_suffix: str) -> None:
    cache_clear_all()
    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name=f"FA {unique_suffix}", slug=f"fa-{unique_suffix}")
    org_b = Organisation(name=f"FB {unique_suffix}", slug=f"fb-{unique_suffix}")
    admin_a = User(
        email=f"aa-{unique_suffix}@example.com",
        display_name="AdminA",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    admin_b = User(
        email=f"ab-{unique_suffix}@example.com",
        display_name="AdminB",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    tenant = User(
        email=f"t-{unique_suffix}@example.com",
        display_name="Tenant",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    worker = User(
        email=f"w-{unique_suffix}@example.com",
        display_name="Worker",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, admin_a, admin_b, tenant, worker])
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
                user_id=tenant.id,
                organisation_id=org_a.id,
                role=HMoreRole.TENANT,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=worker.id,
                organisation_id=org_a.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()

    apply_organisation_rls(db_session, org_a.id)
    ctx_a = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin_a.id)
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, admin_b.id)
    ctx_tenant = _ctx(HMoreRole.TENANT, org_a.id, tenant.id)
    ctx_worker = _ctx(HMoreRole.SUPPORT_WORKER, org_a.id, worker.id)

    # Missing config => unavailable (fail closed).
    decision = ff_service.evaluate_availability(
        db_session, organisation_id=org_a.id, feature_id=FEATURE_NOTES_ANALYSIS, use_cache=False
    )
    assert decision.available is False
    assert decision.reason == "missing_configuration"

    with pytest.raises(HTTPException) as blocked:
        ff_service.require_feature_available(db_session, ctx_a, FEATURE_NOTES_ANALYSIS)
    assert blocked.value.status_code == 403

    # Unsupported feature rejected.
    with pytest.raises(HTTPException) as bad:
        ff_service.update_feature(
            db_session, ctx_a, "ai.agent.does_not_exist", enabled=True, change_reason="nope"
        )
    assert bad.value.status_code == 422

    # Tenant cannot manage.
    with pytest.raises(HTTPException) as tenant_denied:
        ff_service.update_feature(
            db_session, ctx_tenant, FEATURE_NOTES_ANALYSIS, enabled=True, change_reason="hack"
        )
    assert tenant_denied.value.status_code == 403

    # Worker cannot manage.
    with pytest.raises(HTTPException) as worker_denied:
        ff_service.list_organisation_config(db_session, ctx_worker)
    assert worker_denied.value.status_code == 403

    # Admin enables notes analysis.
    enabled = ff_service.update_feature(
        db_session,
        ctx_a,
        FEATURE_NOTES_ANALYSIS,
        enabled=True,
        change_reason="Pilot rollout for notes",
    )
    assert enabled["enabled"] is True
    assert enabled["configured"] is True
    assert ff_service.is_feature_available(
        db_session, organisation_id=org_a.id, feature_id=FEATURE_NOTES_ANALYSIS, use_cache=False
    )

    # Cache populated for org A only.
    cached = cache_get(org_a.id, FEATURE_NOTES_ANALYSIS)
    assert cached == (True, False)
    assert cache_get(org_b.id, FEATURE_NOTES_ANALYSIS) is None

    # Org B cannot see/change org A (IDOR).
    apply_organisation_rls(db_session, org_b.id)
    listed_b = ff_service.list_organisation_config(db_session, ctx_b)
    notes_b = next(i for i in listed_b["items"] if i["feature_id"] == FEATURE_NOTES_ANALYSIS)
    assert notes_b["enabled"] is False
    assert notes_b["configured"] is False

    # Cross-org: B enabling only affects B.
    ff_service.update_feature(db_session, ctx_b, FEATURE_NOTES_ANALYSIS, enabled=True, change_reason="B pilot")
    apply_organisation_rls(db_session, org_a.id)
    assert ff_service.is_feature_available(
        db_session, organisation_id=org_a.id, feature_id=FEATURE_NOTES_ANALYSIS, use_cache=False
    )

    # Disable blocks again + invalidates cache.
    ff_service.update_feature(
        db_session, ctx_a, FEATURE_NOTES_ANALYSIS, enabled=False, change_reason="Pause notes AI"
    )
    with pytest.raises(HTTPException) as blocked2:
        notes_service.run_analysis(db_session, ctx_a, daily_log_id=uuid.uuid4())
    # May be 403 feature or 404 log — feature check runs first.
    assert blocked2.value.status_code == 403

    # Pilot feature: tenant assistant requires pilot_enabled.
    ta = ff_service.update_feature(
        db_session,
        ctx_a,
        FEATURE_TENANT_ASSISTANT,
        enabled=True,
        pilot_enabled=True,
        change_reason="Enable TA pilot",
    )
    assert ta["pilot_enabled"] is True
    assert ff_service.is_feature_available(
        db_session, organisation_id=org_a.id, feature_id=FEATURE_TENANT_ASSISTANT, use_cache=False
    )
    ff_service.update_feature(
        db_session,
        ctx_a,
        FEATURE_TENANT_ASSISTANT,
        enabled=True,
        pilot_enabled=False,
        change_reason="Pause pilot",
    )
    assert (
        ff_service.is_feature_available(
            db_session, organisation_id=org_a.id, feature_id=FEATURE_TENANT_ASSISTANT, use_cache=False
        )
        is False
    )

    # Concurrent revision conflict.
    current = ff_service.get_feature_config(db_session, ctx_a, FEATURE_NOTES_ANALYSIS)
    with pytest.raises(HTTPException) as conflict:
        ff_service.update_feature(
            db_session,
            ctx_a,
            FEATURE_NOTES_ANALYSIS,
            enabled=True,
            expected_revision=999,
            change_reason="stale",
        )
    assert conflict.value.status_code == 409
    _ = current

    # New org defaults — all disabled.
    apply_platform_rls_bypass(db_session)
    new_org = Organisation(name=f"FN {unique_suffix}", slug=f"fn-{unique_suffix}")
    db_session.add(new_org)
    db_session.flush()
    created = ff_service.seed_defaults_for_organisation(
        db_session, organisation_id=new_org.id, actor_user_id=admin_a.id
    )
    assert created == 12
    assert (
        ff_service.is_feature_available(
            db_session, organisation_id=new_org.id, feature_id=FEATURE_NOTES_ANALYSIS, use_cache=False
        )
        is False
    )

    # Audit events present.
    apply_organisation_rls(db_session, org_a.id)
    audits = list(
        db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.organisation_id == org_a.id,
                AuditEvent.action.in_(
                    [
                        audit_events.AI_FEATURE_ENABLED,
                        audit_events.AI_FEATURE_DISABLED,
                        audit_events.AI_FEATURE_EXECUTION_BLOCKED,
                        audit_events.AI_FEATURE_CONFIG_REJECTED,
                        audit_events.AI_FEATURE_PILOT_ENABLED,
                    ]
                ),
            )
        )
    )
    assert len(audits) >= 3

    history = ff_service.list_history(db_session, ctx_a, limit=20)
    assert history["items"]

    # Enablement metadata asserts caps/approval not bypassed.
    meta_events = [a for a in audits if a.action == audit_events.AI_FEATURE_ENABLED]
    if meta_events:
        assert meta_events[0].metadata_json.get("bypasses_usage_caps") is False
        assert meta_events[0].metadata_json.get("bypasses_human_approval") is False
