"""F4.2 staff mobile helpers. No new occupancy count API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.communication.service import message_resource_fields
from app.db.models.enums import HMoreRole
from app.occupancy.service import _public_survey
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission


def test_inbox_resource_fields_are_optional_and_present_when_stored() -> None:
    empty = message_resource_fields(SimpleNamespace())
    assert empty == {"related_resource_type": None, "related_resource_id": None}
    resource_id = uuid.uuid4()
    linked = message_resource_fields(
        SimpleNamespace(related_resource_type="incident", related_resource_id=resource_id)
    )
    assert linked == {"related_resource_type": "incident", "related_resource_id": str(resource_id)}


def test_contractor_cannot_read_caseload_and_support_worker_cannot_decide() -> None:
    assert not role_has_permission(HMoreRole.MAINTENANCE_CONTRACTOR, Permission.SUPPORT_NOTES_READ_ASSIGNED)
    assert not role_has_permission(HMoreRole.MAINTENANCE_CONTRACTOR, Permission.TENANTS_READ)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.APPROVALS_INBOX_READ)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.APPROVALS_DECIDE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.APPROVALS_DECIDE)
    assert role_has_permission(HMoreRole.MAINTENANCE_CONTRACTOR, Permission.MAINTENANCE_PHOTO_UPLOAD)


def test_public_survey_does_not_include_a_live_people_count() -> None:
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        id=uuid.uuid4(),
        organisation_id=uuid.uuid4(),
        property_id=uuid.uuid4(),
        status="completed",
        survey_date=None,
        surveyor_user_id=None,
        surveyor_display_name=None,
        site_contact_notes=None,
        building_assessment=None,
        facilities_assessment=None,
        health_safety_assessment=None,
        accessibility_assessment=None,
        camera_feasibility_notes="No camera count is collected.",
        feasibility_status="further_assessment_required",
        feasibility_summary="Survey only",
        missing_information=None,
        recommendations=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    public = _public_survey(row)
    assert "people_count" not in public
    assert "occupant_count" not in public
    assert "live_count" not in public
    assert public["feasibility_summary"] == "Survey only"
    assert "camera" in public["disclaimer"].lower()

