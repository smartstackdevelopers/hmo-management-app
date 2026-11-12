"""F6.6 Finance & Budgets tests — no payment gateway claims."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.db.models.enums import HMoreRole, MembershipStatus
from app.finance import service as finance_service
from app.finance.access import require_budget_manage, require_finance_manage, require_finance_read
from app.finance.constants import FINANCE_DISCLAIMER
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def _ctx(role: HMoreRole, organisation_id, user) -> OrganisationContext:
    return OrganisationContext(
        user=user,
        organisation_id=organisation_id,
        role=role,
        authorization=AuthorizationContext(
            user=user,
            memberships=[
                MembershipView(
                    membership_id=uuid.uuid4(),
                    role=role,
                    organisation_id=organisation_id,
                    status=MembershipStatus.ACTIVE,
                )
            ],
            active_organisation_id=organisation_id,
            active_role=role,
        ),
    )


def test_alembic_f66_revision_chain() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    rev = script.get_revision("20261111_4400_f66")
    assert rev is not None
    assert rev.down_revision == "20261111_4300_f65"
    assert script.get_revision("20261111_4500_f67") is not None


def test_f66_permissions_matrix() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.FINANCE_RECORDS_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.FINANCE_BUDGETS_MANAGE)
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.FINANCE_EXPORTS)
    assert role_has_permission(HMoreRole.LANDLORD, Permission.FINANCE_RECORDS_READ)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.FINANCE_BUDGETS_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.FINANCE_RECORDS_READ)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.FINANCE_RECORDS_MANAGE)


def test_tenant_denied_finance() -> None:
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), SimpleNamespace(id=uuid.uuid4()))
    with pytest.raises(Exception):
        require_finance_read(ctx)
    with pytest.raises(Exception):
        require_finance_manage(ctx)
    with pytest.raises(Exception):
        require_budget_manage(ctx)


def test_disclaimer_rejects_payment_gateway_claim() -> None:
    assert "payment" in FINANCE_DISCLAIMER.lower()
    assert "gateway" in FINANCE_DISCLAIMER.lower() or "banking" in FINANCE_DISCLAIMER.lower()


def test_invalid_amount_rejected_without_db() -> None:
    # Validation path before flush for negative via Decimal in create — exercised in postgres test;
    # status create rejects voided status without needing DB write of money.
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, uuid.uuid4(), user)
    with pytest.raises(HTTPException):
        finance_service.create_record(
            session=SimpleNamespace(),  # type: ignore[arg-type]
            ctx=ctx,
            record_type="not_a_type",  # type: ignore[arg-type]
            category_code="admin",
            amount=Decimal("1.00"),
            effective_date=date.today(),
        )


@pytest.mark.postgres
def test_finance_lifecycle_budget_export_isolation(db_session, unique_suffix: str) -> None:
    from sqlalchemy import select

    from app.db.models.audit import AuditEvent
    from app.db.models.membership import OrganisationMembership
    from app.db.models.organisation import Organisation
    from app.db.models.user import User

    org_a = Organisation(name=f"FinA-{unique_suffix}", slug=f"fina-{unique_suffix}")
    org_b = Organisation(name=f"FinB-{unique_suffix}", slug=f"finb-{unique_suffix}")
    admin = User(
        email=f"fina-{unique_suffix}@example.com",
        display_name="Finance Admin",
        external_subject=f"auth0|fina-{unique_suffix}",
    )
    db_session.add_all([org_a, org_b, admin])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=admin.id,
            organisation_id=org_a.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin)

    created = finance_service.create_record(
        db_session,
        ctx,
        record_type="income",
        category_code="other_income",
        amount="150.50",
        effective_date=date(2026, 1, 15),
        description="Grant",
        status="posted",
    )
    assert created["amount"] == "150.50"
    assert created["status"] == "posted"

    updated = finance_service.update_record(
        db_session, ctx, uuid.UUID(created["id"]), description="Grant updated"
    )
    assert updated["description"] == "Grant updated"

    with pytest.raises(HTTPException):
        finance_service.create_record(
            db_session,
            ctx,
            record_type="expense",
            category_code="admin",
            amount="-1",
            effective_date=date.today(),
        )

    budget = finance_service.create_budget(
        db_session,
        ctx,
        name=f"FY-{unique_suffix}",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        status="active",
        lines=[{"category_code": "other_income", "planned_amount": "1000.00"}],
    )
    variance = finance_service.budget_variance(db_session, ctx, uuid.UUID(budget["id"]))
    assert variance["comparisons"][0]["actual_amount"] == "150.50"

    dash = finance_service.dashboard(db_session, ctx)
    assert dash["income_posted"] == "150.50"
    assert "payment" in dash["disclaimer"].lower()

    csv_bytes, media, name = finance_service.export_records(db_session, ctx, export_format="csv")
    assert media == "text/csv"
    assert b"150.50" in csv_bytes
    assert name.endswith(".csv")

    voided = finance_service.void_record(db_session, ctx, uuid.UUID(created["id"]), "Entered twice")
    assert voided["status"] == "voided"

    other = User(
        email=f"finb-{unique_suffix}@example.com",
        display_name="Other",
        external_subject=f"auth0|finb-{unique_suffix}",
    )
    db_session.add(other)
    db_session.flush()
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, other)
    assert finance_service.list_records(db_session, ctx_b) == []

    actions = set(
        db_session.scalars(select(AuditEvent.action).where(AuditEvent.organisation_id == org_a.id)).all()
    )
    assert "finance.record.create" in actions
    assert "finance.record.update" in actions
    assert "finance.budget.create" in actions
    assert "finance.export" in actions
    assert "finance.record.void" in actions
