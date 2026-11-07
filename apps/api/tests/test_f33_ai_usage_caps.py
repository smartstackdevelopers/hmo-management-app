"""F3.3 PostgreSQL tests — budgets, caps, metering, RLS isolation."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.ai_usage.budget import (
    BudgetExceededError,
    budget_status_snapshot,
    get_active_budget,
    reserve_budget,
    upsert_budget,
)
from app.ai_usage.cost import upsert_pricing
from app.ai_usage.dashboard import organisation_dashboard, platform_dashboard
from app.ai_usage.metering import record_and_reconcile
from app.ai_usage.period import period_key_for
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.ai_usage import AiBudgetReservation, AiUsageRecord, OrganisationAiBudget
from app.db.models.enums import HMoreRole, MembershipStatus
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
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


def _seed_org(session: Session, suffix: str) -> tuple[Organisation, User]:
    org = Organisation(name=f"AI Org {suffix}", slug=f"ai-{suffix}")
    user = User(
        email=f"ai-{suffix}@example.com",
        display_name="AI Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    session.add_all([org, user])
    session.flush()
    session.add(
        OrganisationMembership(
            user_id=user.id,
            organisation_id=org.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    session.flush()
    return org, user


@pytest.mark.postgres
def test_f33_budget_create_and_invalid_rejected(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, user = _seed_org(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, user.id)

    with pytest.raises(Exception):
        from app.ai_usage.schemas import BudgetUpsert

        BudgetUpsert(
            monthly_limit=Decimal("-1"),
            effective_from=date.today(),
        )

    budget = upsert_budget(
        db_session,
        ctx,
        org.id,
        {
            "monthly_limit": Decimal("10.0000"),
            "currency": "GBP",
            "effective_from": date.today(),
            "warning_threshold_pct": Decimal("75.00"),
            "default_reservation_amount": Decimal("1.0000"),
        },
    )
    assert budget.monthly_limit == Decimal("10.0000")
    assert get_active_budget(db_session, org.id) is not None
    history = list(
        db_session.scalars(
            select(OrganisationAiBudget).where(OrganisationAiBudget.organisation_id == org.id)
        )
    )
    assert len(history) == 1


@pytest.mark.postgres
def test_f33_hard_cap_rejection_and_visible_status(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, user = _seed_org(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.SUPER_ADMIN, org.id, user.id)
    upsert_budget(
        db_session,
        ctx,
        org.id,
        {
            "monthly_limit": Decimal("1.0000"),
            "currency": "GBP",
            "effective_from": date.today(),
            "default_reservation_amount": Decimal("0.6000"),
        },
    )
    upsert_pricing(
        db_session,
        {
            "provider": "mock",
            "model_id": "mock-basic",
            "pricing_version": "test-v1",
            "currency": "GBP",
            "input_price_per_1k_tokens": Decimal("1.000000"),
            "output_price_per_1k_tokens": Decimal("1.000000"),
            "effective_from": date.today(),
            "active": True,
        },
    )

    r1 = reserve_budget(
        db_session,
        request_id=f"req-{unique_suffix}-1",
        organisation_id=org.id,
        user_id=user.id,
        feature_id="ai.infra.routing",
        workflow_id="foundation_routed_echo",
    )
    assert r1["permitted"] is True

    record_and_reconcile(
        db_session,
        request_id=f"req-{unique_suffix}-1",
        organisation_id=org.id,
        execution_status="completed",
        feature_id="ai.infra.routing",
        workflow_id="foundation_routed_echo",
        user_id=user.id,
        provider="mock",
        model_id="mock-basic",
        input_tokens=500,
        output_tokens=500,
        cache_hit=False,
    )

    with pytest.raises(BudgetExceededError) as exc:
        reserve_budget(
            db_session,
            request_id=f"req-{unique_suffix}-2",
            organisation_id=org.id,
            user_id=user.id,
            feature_id="ai.infra.routing",
            workflow_id="foundation_routed_echo",
        )
    assert "usage limit" in exc.value.message.lower() or "limit" in exc.value.message.lower()
    http = exc.value.to_http()
    assert http.status_code == 402
    assert http.detail["error"] == "ai_budget_exceeded"

    rejected = db_session.scalars(
        select(AiUsageRecord).where(AiUsageRecord.request_id == f"req-{unique_suffix}-2")
    ).first()
    assert rejected is not None
    assert rejected.execution_status == "rejected_budget"


@pytest.mark.postgres
def test_f33_duplicate_request_idempotent(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, user = _seed_org(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.SUPER_ADMIN, org.id, user.id)
    upsert_budget(
        db_session,
        ctx,
        org.id,
        {
            "monthly_limit": Decimal("50.0000"),
            "currency": "GBP",
            "effective_from": date.today(),
            "default_reservation_amount": Decimal("0.0500"),
        },
    )
    rid = f"dup-{unique_suffix}"
    a = reserve_budget(
        db_session,
        request_id=rid,
        organisation_id=org.id,
        user_id=user.id,
        feature_id="ai.infra.foundation",
        workflow_id="foundation_echo",
    )
    b = reserve_budget(
        db_session,
        request_id=rid,
        organisation_id=org.id,
        user_id=user.id,
        feature_id="ai.infra.foundation",
        workflow_id="foundation_echo",
    )
    assert a["reservation_id"] == b["reservation_id"]
    assert b["idempotent"] is True

    first = record_and_reconcile(
        db_session,
        request_id=rid,
        organisation_id=org.id,
        execution_status="completed",
        feature_id="ai.infra.foundation",
        workflow_id="foundation_echo",
        input_tokens=10,
        output_tokens=10,
        provider="mock",
        model_id="x",
    )
    second = record_and_reconcile(
        db_session,
        request_id=rid,
        organisation_id=org.id,
        execution_status="completed",
        feature_id="ai.infra.foundation",
        workflow_id="foundation_echo",
        input_tokens=999,
        output_tokens=999,
        provider="mock",
        model_id="x",
    )
    assert first.id == second.id
    assert second.input_tokens == 10


@pytest.mark.postgres
def test_f33_failed_request_releases_reservation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, user = _seed_org(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.SUPER_ADMIN, org.id, user.id)
    upsert_budget(
        db_session,
        ctx,
        org.id,
        {
            "monthly_limit": Decimal("5.0000"),
            "currency": "GBP",
            "effective_from": date.today(),
            "default_reservation_amount": Decimal("2.0000"),
        },
    )
    rid = f"fail-{unique_suffix}"
    reserve_budget(
        db_session,
        request_id=rid,
        organisation_id=org.id,
        user_id=user.id,
        feature_id="ai.infra.routing",
        workflow_id="foundation_routed_echo",
    )
    record_and_reconcile(
        db_session,
        request_id=rid,
        organisation_id=org.id,
        execution_status="failed",
        feature_id="ai.infra.routing",
        workflow_id="foundation_routed_echo",
    )
    res = db_session.scalars(select(AiBudgetReservation).where(AiBudgetReservation.request_id == rid)).one()
    assert res.status == "released"
    snap = budget_status_snapshot(db_session, org.id)
    assert Decimal(snap["open_reservations"]) == Decimal("0")
    assert Decimal(snap["actual_spend"]) == Decimal("0")


@pytest.mark.postgres
def test_f33_cross_org_usage_isolation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org_a, user_a = _seed_org(db_session, f"{unique_suffix}a")
    org_b, _user_b = _seed_org(db_session, f"{unique_suffix}b")
    db_session.add(
        AiUsageRecord(
            id=uuid.uuid4(),
            organisation_id=org_a.id,
            request_id=f"iso-a-{unique_suffix}",
            workflow_id="foundation_echo",
            feature_id="ai.infra.foundation",
            execution_status="completed",
            cost_status="unavailable",
            period_key=period_key_for(),
            executed_at=datetime.now(timezone.utc),
            metadata_json={},
        )
    )
    db_session.flush()

    apply_organisation_rls(db_session, org_b.id)
    rows = list(db_session.scalars(select(AiUsageRecord)).all())
    assert rows == []

    apply_organisation_rls(db_session, org_a.id)
    rows_a = list(db_session.scalars(select(AiUsageRecord)).all())
    assert len(rows_a) == 1
    assert rows_a[0].organisation_id == org_a.id


@pytest.mark.postgres
def test_f33_dashboard_aggregations(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, user = _seed_org(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.SUPER_ADMIN, org.id, user.id)
    upsert_budget(
        db_session,
        ctx,
        org.id,
        {
            "monthly_limit": Decimal("100.0000"),
            "currency": "GBP",
            "effective_from": date.today(),
        },
    )
    upsert_pricing(
        db_session,
        {
            "provider": "mock",
            "model_id": "mock-basic",
            "pricing_version": "dash-v1",
            "currency": "GBP",
            "input_price_per_1k_tokens": Decimal("1.000000"),
            "output_price_per_1k_tokens": Decimal("2.000000"),
            "effective_from": date.today(),
            "active": True,
        },
    )
    rid = f"dash-{unique_suffix}"
    reserve_budget(
        db_session,
        request_id=rid,
        organisation_id=org.id,
        user_id=user.id,
        feature_id="ai.infra.routing",
        workflow_id="foundation_routed_echo",
        reserved_amount=Decimal("0.0100"),
    )
    record_and_reconcile(
        db_session,
        request_id=rid,
        organisation_id=org.id,
        execution_status="completed",
        feature_id="ai.infra.routing",
        workflow_id="foundation_routed_echo",
        provider="mock",
        model_id="mock-basic",
        input_tokens=1000,
        output_tokens=1000,
        cache_hit=False,
        escalation_occurred=True,
    )
    org_dash = organisation_dashboard(db_session, org.id)
    assert org_dash["empty"] is False
    assert org_dash["totals"]["execution_count"] == 1
    assert Decimal(org_dash["totals"]["actual_cost"]) == Decimal("3.000000")
    assert org_dash["by_feature"][0]["feature_id"] == "ai.infra.routing"

    plat = platform_dashboard(db_session)
    assert plat["scope"] == "platform"
    assert any(o["organisation_id"] == str(org.id) for o in plat["organisations"])


@pytest.mark.postgres
def test_f33_concurrent_reservations_do_not_overspend(
    migrated_engine, unique_suffix: str
) -> None:
    """Two concurrent reserves against a tiny budget — at most one may succeed."""
    SessionLocal = sessionmaker(bind=migrated_engine, autoflush=False, future=True)
    setup = SessionLocal()
    apply_platform_rls_bypass(setup)
    org, user = _seed_org(setup, f"c{unique_suffix}")
    ctx = _ctx(HMoreRole.SUPER_ADMIN, org.id, user.id)
    upsert_budget(
        setup,
        ctx,
        org.id,
        {
            "monthly_limit": Decimal("1.0000"),
            "currency": "GBP",
            "effective_from": date.today(),
            "default_reservation_amount": Decimal("0.8000"),
        },
    )
    setup.commit()
    org_id = org.id
    user_id = user.id
    setup.close()

    results: list[str] = []

    def attempt(i: int) -> str:
        s = SessionLocal()
        try:
            apply_platform_rls_bypass(s)
            reserve_budget(
                s,
                request_id=f"conc-{unique_suffix}-{i}",
                organisation_id=org_id,
                user_id=user_id,
                feature_id="ai.infra.routing",
                workflow_id="foundation_routed_echo",
            )
            s.commit()
            return "ok"
        except BudgetExceededError:
            s.commit()
            return "rejected"
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [1, 2]))

    assert results.count("ok") == 1
    assert results.count("rejected") == 1


def test_f33_rbac_matrix_roles() -> None:
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.AI_PLATFORM_COST_VIEW)
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.AI_BUDGET_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.AI_COST_DASHBOARD_VIEW)
    assert not role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.AI_BUDGET_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.AI_USAGE_READ)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.AI_COST_DASHBOARD_VIEW)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AI_BUDGET_MANAGE)
    assert not role_has_permission(HMoreRole.MAINTENANCE_CONTRACTOR, Permission.AI_USAGE_READ)
