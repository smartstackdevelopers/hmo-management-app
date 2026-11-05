"""F1.10 occupancy site-survey tests. No camera functionality covered or claimed."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.db.models.enums import HMoreRole, MembershipStatus
from app.main import app
from app.occupancy.access import require_survey_read, require_survey_write
from app.occupancy.schemas import FindingCreate, SurveyUpdate
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def test_occupancy_permissions_for_survey_roles() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.OCCUPANCY_ALERTS_MANAGE)
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.OCCUPANCY_READ)
    assert role_has_permission(HMoreRole.LANDLORD, Permission.INSPECTIONS_MANAGE)
    assert not role_has_permission(HMoreRole.TENANT, Permission.OCCUPANCY_ALERTS_MANAGE)


def test_survey_write_denied_for_tenant_context() -> None:
    org_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4())
    authz = AuthorizationContext(
        user=user,  # type: ignore[arg-type]
        memberships=[
            MembershipView(
                membership_id=uuid.uuid4(),
                role=HMoreRole.TENANT,
                organisation_id=org_id,
                status=MembershipStatus.ACTIVE,
            )
        ],
        active_organisation_id=org_id,
        active_role=HMoreRole.TENANT,
    )
    ctx = OrganisationContext(
        user=user,  # type: ignore[arg-type]
        organisation_id=org_id,
        role=HMoreRole.TENANT,
        authorization=authz,
    )
    with pytest.raises(HTTPException) as exc:
        require_survey_write(ctx)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException):
        require_survey_read(ctx)


def test_feasibility_status_validation() -> None:
    with pytest.raises(ValidationError):
        SurveyUpdate(feasibility_status="legally_certified")  # type: ignore[arg-type]
    ok = SurveyUpdate(feasibility_status="suitable_with_actions")
    assert ok.feasibility_status == "suitable_with_actions"


def test_finding_requires_description() -> None:
    with pytest.raises(ValidationError):
        FindingCreate(category="fire", description="")


def test_unauthenticated_survey_api_returns_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/occupancy-surveys").status_code == 401
    assert client.post(
        "/api/v1/occupancy-surveys", json={"property_id": str(uuid.uuid4())}
    ).status_code == 401


def _org_ctx(role: HMoreRole, org_id: uuid.UUID, user_id: uuid.UUID) -> OrganisationContext:
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


@pytest.mark.postgres
def test_survey_crud_findings_and_cross_org_denial(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, OrganisationMembership, Property, User
    from app.occupancy.schemas import FindingCreate, SurveyCreate, SurveyUpdate
    from app.occupancy import service as survey_service
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="OA", slug=f"oa-{unique_suffix}")
    org_b = Organisation(name="OB", slug=f"ob-{unique_suffix}")
    user_a = User(
        email=f"oa-{unique_suffix}@example.com",
        display_name="A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    user_b = User(
        email=f"ob-{unique_suffix}@example.com",
        display_name="B",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, user_a, user_b])
    db_session.flush()
    prop_a = Property(
        organisation_id=org_a.id,
        name="Site A",
        address_line1="1 High St",
        city="London",
        postcode="E1 1AA",
    )
    prop_b = Property(
        organisation_id=org_b.id,
        name="Site B",
        address_line1="2 High St",
        city="London",
        postcode="E1 2BB",
    )
    db_session.add_all(
        [
            prop_a,
            prop_b,
            OrganisationMembership(
                user_id=user_a.id,
                organisation_id=org_a.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=user_b.id,
                organisation_id=org_b.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()

    ctx_a = _org_ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, user_a.id)
    ctx_b = _org_ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, user_b.id)

    apply_organisation_rls(db_session, org_a.id)
    created = survey_service.create_survey(
        db_session, ctx_a, SurveyCreate(property_id=prop_a.id, surveyor_display_name="A Surveyor")
    )
    survey_id = uuid.UUID(created["id"])
    assert "not a legal" in created["disclaimer"].lower()

    survey_service.update_survey(
        db_session,
        ctx_a,
        survey_id,
        SurveyUpdate(
            status="in_progress",
            building_assessment={"general_condition": "fair"},
            facilities_assessment={"water_supply": "available"},
        ),
    )
    finding = survey_service.add_finding(
        db_session,
        ctx_a,
        survey_id,
        FindingCreate(
            category="fire_safety",
            severity="high",
            description="Exit signage missing on floor 2",
            recommended_action="Install compliant signage after competent review",
        ),
    )
    assert finding["status"] == "open"

    completed = survey_service.update_survey(
        db_session,
        ctx_a,
        survey_id,
        SurveyUpdate(
            status="completed",
            feasibility_status="suitable_with_actions",
            feasibility_summary="Suitable after signage remediation",
            recommendations="Complete fire signage actions before any occupancy programme.",
        ),
    )
    assert completed["feasibility_status"] == "suitable_with_actions"

    apply_organisation_rls(db_session, org_b.id)
    with pytest.raises(HTTPException) as denied:
        survey_service.get_survey(db_session, ctx_b, survey_id)
    assert denied.value.status_code in {403, 404}
