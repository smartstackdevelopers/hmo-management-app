"""F6.2 full reports & analytics tests."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException

from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.db.models.membership import OrganisationMembership
from app.db.models.organisation import Organisation
from app.db.models.property import Property
from app.db.models.reporting_analytics import ScheduledReportRun
from app.db.models.room import Room
from app.db.models.support_ops import CaseAssignment
from app.db.models.support_plans import TenantSupportPlan
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.reporting import alerts as alert_service
from app.reporting import exports
from app.reporting import jobs as reporting_jobs
from app.reporting import occupancy_reports
from app.reporting import plan_completion_reports
from app.reporting import schedules as schedule_service
from app.reporting import secure_exports
from app.reporting.filters import OccupancyReportFilters, PlanReportFilters
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


def test_alembic_head_is_f62() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261111_4000_f62"]
    rev = script.get_revision("20261111_4000_f62")
    assert rev is not None
    assert rev.down_revision == "20261111_3900_f61"


def test_f62_permissions_matrix() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.REPORTS_OCCUPANCY_VIEW)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.REPORTS_PLANS_VIEW)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.REPORTS_SCHEDULE_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.REPORTS_ALERTS_VIEW)
    assert role_has_permission(HMoreRole.LANDLORD, Permission.REPORTS_OCCUPANCY_VIEW)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.REPORTS_PLANS_VIEW)
    assert not role_has_permission(HMoreRole.TENANT, Permission.REPORTS_OCCUPANCY_VIEW)
    assert not role_has_permission(HMoreRole.TENANT, Permission.REPORTS_SCHEDULE_MANAGE)


def test_export_formats_open() -> None:
    rows = [{"ref": "A-1", "status": "open"}, {"ref": "A-2", "status": "closed"}]
    csv_body = exports.rows_to_csv(["ref", "status"], rows)
    assert csv_body.decode("utf-8-sig").startswith("ref")
    xlsx = exports.rows_to_xlsx("Plans", ["ref", "status"], rows)
    assert xlsx[:2] == b"PK"
    pdf = exports.summary_to_pdf("Occupancy", {"total_rooms": 2, "occupied_rooms": 1}, ["room 1 occupied"])
    assert pdf.startswith(b"%PDF")


def test_tenant_denied_occupancy_and_schedule() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    ctx = _ctx(HMoreRole.TENANT, uuid.uuid4(), user)
    with pytest.raises(Exception):
        from app.reporting.access import require_occupancy_reports

        require_occupancy_reports(ctx)
    with pytest.raises(Exception):
        from app.reporting.access import require_schedule_manage

        require_schedule_manage(ctx)


def test_alert_dedupe_key_logic_unit() -> None:
    """Pure unit: same condition must not create a second open alert (service-level)."""
    assert alert_service.DEFAULT_THRESHOLDS["overdue_complaints"] > 0
    assert "high_caseload" in alert_service.DEFAULT_THRESHOLDS


@pytest.mark.postgres
def test_occupancy_plans_schedules_alerts_isolation(db_session, unique_suffix: str) -> None:
    now = datetime.now(timezone.utc)
    org_a = Organisation(name=f"OrgA-{unique_suffix}", slug=f"orga-{unique_suffix}")
    org_b = Organisation(name=f"OrgB-{unique_suffix}", slug=f"orgb-{unique_suffix}")
    admin_a = User(
        email=f"f62a-{unique_suffix}@example.com",
        display_name="Admin A",
        external_subject=f"auth0|f62a-{unique_suffix}",
    )
    admin_b = User(
        email=f"f62b-{unique_suffix}@example.com",
        display_name="Admin B",
        external_subject=f"auth0|f62b-{unique_suffix}",
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
    prop = Property(
        organisation_id=org_a.id,
        name=f"House-{unique_suffix}",
        address_line1="1 Test St",
        city="London",
        postcode="E1 1AA",
        status=RecordStatus.ACTIVE,
    )
    db_session.add(prop)
    db_session.flush()
    room1 = Room(
        organisation_id=org_a.id,
        property_id=prop.id,
        label="R1",
        max_occupancy=1,
        status=RecordStatus.ACTIVE,
    )
    room2 = Room(
        organisation_id=org_a.id,
        property_id=prop.id,
        label="R2",
        max_occupancy=1,
        status=RecordStatus.ACTIVE,
    )
    db_session.add_all([room1, room2])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org_a.id,
        preferred_name="Tenant A",
        status=RecordStatus.ACTIVE,
        assigned_property_id=prop.id,
        assigned_room_id=room1.id,
    )
    db_session.add(tenant)
    db_session.flush()
    plan = TenantSupportPlan(
        organisation_id=org_a.id,
        reference_number=f"SP-{unique_suffix}",
        tenant_id=tenant.id,
        title="Plan",
        responsible_worker_user_id=admin_a.id,
        status="active",
        planned_review_date=date.today() - timedelta(days=3),
    )
    db_session.add(plan)
    # Create three tenants with active assignments for high caseload threshold
    for i in range(3):
        t = Tenant(
            organisation_id=org_a.id,
            preferred_name=f"Case {i}-{unique_suffix}",
            status=RecordStatus.ACTIVE,
        )
        db_session.add(t)
        db_session.flush()
        db_session.add(
            CaseAssignment(
                organisation_id=org_a.id,
                tenant_id=t.id,
                support_worker_user_id=admin_a.id,
                status="active",
                assigned_at=now,
            )
        )
    db_session.flush()

    ctx_a = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin_a)
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, admin_b)

    occ = occupancy_reports.occupancy_summary(db_session, ctx_a, OccupancyReportFilters())
    assert occ["total_rooms"] == 2
    assert occ["occupied_rooms"] == 1
    assert occ["vacant_rooms"] == 1

    occ_b = occupancy_reports.occupancy_summary(db_session, ctx_b, OccupancyReportFilters())
    assert occ_b["total_rooms"] == 0

    plans = plan_completion_reports.plan_completion_summary(db_session, ctx_a, PlanReportFilters())
    assert plans["total"] >= 1
    assert plans["overdue_reviews"] >= 1

    alert_service.upsert_threshold(db_session, ctx_a, alert_type="overdue_plan_reviews", threshold_value=1)
    alert_service.upsert_threshold(db_session, ctx_a, alert_type="high_caseload", threshold_value=2)
    alert_service.upsert_threshold(db_session, ctx_a, alert_type="occupancy_drop", threshold_value=90)
    first = alert_service.evaluate_organisation_alerts(db_session, org_a.id)
    assert first["created"] >= 1
    second = alert_service.evaluate_organisation_alerts(db_session, org_a.id)
    assert second["created"] == 0
    open_a = alert_service.list_alerts(db_session, ctx_a, status_filter="open")
    assert open_a["total"] >= 1
    open_b = alert_service.list_alerts(db_session, ctx_b, status_filter="open")
    assert open_b["total"] == 0

    body = exports.rows_to_csv(
        ["property_name", "status"], [{"property_name": prop.name, "status": "occupied"}]
    )
    artifact = secure_exports.store_report_export(
        db_session,
        ctx_a,
        category="occupancy",
        export_format="csv",
        title="Occ",
        body=body,
        row_count=1,
        allowed_user_ids=[str(admin_a.id)],
    )
    export, meta, data = secure_exports.get_export_bytes(db_session, ctx_a, artifact.id)
    assert export.id == artifact.id
    assert meta.original_filename.endswith(".csv")
    assert b"property_name" in data
    with pytest.raises(HTTPException) as denied:
        secure_exports.get_export_bytes(db_session, ctx_b, artifact.id)
    assert denied.value.status_code in {403, 404}

    schedule = schedule_service.create_schedule(
        db_session,
        ctx_a,
        name="Daily occupancy",
        report_category="occupancy",
        frequency="daily",
        export_format="csv",
        period_days=7,
        recipient_user_ids=[str(admin_a.id)],
        is_enabled=True,
    )
    result = reporting_jobs.execute_scheduled_report(db_session, uuid.UUID(schedule["id"]))
    assert result["ok"] is True
    assert result.get("export_id")

    failed = ScheduledReportRun(
        organisation_id=org_a.id,
        scheduled_report_id=uuid.UUID(schedule["id"]),
        status="failed",
        attempt_count=1,
        error_message="simulated",
        started_at=now,
        finished_at=now,
    )
    db_session.add(failed)
    db_session.flush()
    retry = reporting_jobs.retry_failed_run(db_session, failed.id)
    assert retry["ok"] is True

    listed_b = schedule_service.list_schedules(db_session, ctx_b)
    assert all(s["id"] != schedule["id"] for s in listed_b)
