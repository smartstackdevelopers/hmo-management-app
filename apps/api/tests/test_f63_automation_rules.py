"""F6.3 automation rules engine tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.automation import engine as automation_engine
from app.automation import service as automation_service
from app.automation.constants import FORBIDDEN_ACTION_KEYS, TRIGGER_CONDITIONS
from app.db.models.automation import AutomationRuleRun
from app.db.models.complaints import Complaint
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.membership import OrganisationMembership
from app.db.models.organisation import Organisation
from app.db.models.user import User
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


def test_alembic_f63_revision_chain() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    rev = script.get_revision("20261111_4100_f63")
    assert rev is not None
    assert rev.down_revision == "20261111_4000_f62"
    # Head advances with later Phase 6 features; F6.3 remains in the chain.
    assert "20261111_4100_f63" in script.get_bases() or script.get_revision("20261111_4200_f64") is not None


def test_f63_permissions_matrix() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.AUTOMATION_RULES_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.AUTOMATION_RULES_READ)
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.AUTOMATION_RULES_MANAGE)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AUTOMATION_ESCALATIONS_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.AUTOMATION_RULES_MANAGE)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.AUTOMATION_RULES_MANAGE)


def test_forbidden_actions_blocked_on_create() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, uuid.uuid4(), user)
    # Session not needed for validation path before DB write — use a dummy with raise on add
    with pytest.raises(HTTPException) as exc:
        automation_service.create_rule(
            session=SimpleNamespace(),  # type: ignore[arg-type]
            ctx=ctx,
            name="Bad",
            description=None,
            category="escalation",
            trigger_condition="complaint_overdue",
            trigger_config={},
            action_type="escalate_record",
            action_config={"approve_housing_application": True},
            frequency="daily",
        )
    assert exc.value.status_code == 400
    assert "Forbidden" in str(exc.value.detail)


def test_tenant_cannot_manage_rules() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), user)
    with pytest.raises(Exception):
        from app.automation.access import require_rules_manage

        require_rules_manage(ctx)


def test_trigger_catalog_covers_required_areas() -> None:
    required = {
        "appointment_upcoming",
        "support_plan_review_overdue",
        "task_overdue",
        "inspection_upcoming",
        "document_expiry",
        "complaint_overdue",
        "maintenance_high_priority",
        "followup_missed",
        "safeguarding_followup_overdue",
        "compliance_scheduled_sweep",
    }
    assert required.issubset(TRIGGER_CONDITIONS)
    assert "approve_housing_application" in FORBIDDEN_ACTION_KEYS


@pytest.mark.postgres
def test_rule_lifecycle_escalation_dedupe_and_isolation(db_session, unique_suffix: str) -> None:
    now = datetime.now(timezone.utc)
    org_a = Organisation(name=f"AutoA-{unique_suffix}", slug=f"autoa-{unique_suffix}")
    org_b = Organisation(name=f"AutoB-{unique_suffix}", slug=f"autob-{unique_suffix}")
    admin_a = User(
        email=f"autoa-{unique_suffix}@example.com",
        display_name="Admin A",
        external_subject=f"auth0|autoa-{unique_suffix}",
    )
    admin_b = User(
        email=f"autob-{unique_suffix}@example.com",
        display_name="Admin B",
        external_subject=f"auth0|autob-{unique_suffix}",
    )
    db_session.add_all([org_a, org_b, admin_a, admin_b])
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
        ]
    )
    complaint = Complaint(
        organisation_id=org_a.id,
        reference_number=f"CMP-{unique_suffix}",
        title="Leak",
        description="Bathroom leak",
        status="under_review",
        priority="high",
        category_code="maintenance",
        response_due_at=now - timedelta(days=2),
        assigned_user_id=admin_a.id,
        submitted_by_user_id=admin_a.id,
        submitted_at=now - timedelta(days=3),
    )
    db_session.add(complaint)
    db_session.flush()

    ctx_a = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin_a)
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, admin_b)

    created = automation_service.create_rule(
        db_session,
        ctx_a,
        name="Escalate overdue complaints",
        description="Test",
        category="escalation",
        trigger_condition="complaint_overdue",
        trigger_config={},
        action_type="escalate_record",
        action_config={
            "recipient_role": "organisation_admin",
            "channels": ["in_app"],
            "escalation_level": 1,
            "severity": "high",
        },
        frequency="daily",
        is_enabled=True,
    )
    rule_id = uuid.UUID(created["id"])

    updated = automation_service.update_rule(db_session, ctx_a, rule_id, is_enabled=True)
    assert updated["is_enabled"] is True

    first = automation_engine.execute_rule(db_session, rule_id, force=True)
    assert first.get("ok") is True
    second = automation_engine.execute_rule(db_session, rule_id, force=True)
    # Same-day idempotency should skip duplicate run or create zero new escalations
    assert second.get("ok") is True
    assert second.get("skipped") or (second.get("result") or {}).get("escalations_created", 0) == 0

    esc_a = automation_service.list_escalations(db_session, ctx_a, status_filter="open")
    assert len(esc_a) >= 1
    esc_b = automation_service.list_escalations(db_session, ctx_b)
    assert all(e["id"] != esc_a[0]["id"] for e in esc_b)

    ack = automation_service.update_escalation_status(
        db_session, ctx_a, uuid.UUID(esc_a[0]["id"]), new_status="acknowledged"
    )
    assert ack["status"] == "acknowledged"

    # Failed run retry path
    failed = AutomationRuleRun(
        organisation_id=org_a.id,
        rule_id=rule_id,
        status="failed",
        idempotency_key=f"retry-test-{unique_suffix}",
        attempt_count=1,
        error_message="simulated",
        started_at=now,
        finished_at=now,
    )
    db_session.add(failed)
    db_session.flush()
    from app.automation import jobs as automation_jobs

    retry = automation_jobs.retry_failed_run(db_session, failed.id)
    assert retry.get("ok") is True

    # Org B cannot see org A rules
    listed_b = automation_service.list_rules(db_session, ctx_b)
    assert all(r["id"] != created["id"] for r in listed_b)

    deactivated = automation_service.update_rule(db_session, ctx_a, rule_id, is_enabled=False)
    assert deactivated["is_enabled"] is False
    deleted = automation_service.delete_rule(db_session, ctx_a, rule_id)
    assert deleted["deleted"] is True
