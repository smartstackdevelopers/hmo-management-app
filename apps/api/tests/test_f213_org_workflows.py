"""F2.13 organisation workflows tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.enums import HMoreRole, MembershipStatus
from app.org_workflows import form_schema, sharing, workflows
from app.org_workflows.schemas import SharingGrantCreate, WorkflowCreate, WorkflowStep
from app.rbac.context import AuthorizationContext, MembershipView
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


def test_form_schema_rejects_script() -> None:
    with pytest.raises(Exception):
        form_schema.validate_form_schema(
            {
                "fields": [
                    {
                        "key": "note",
                        "type": "short_text",
                        "label": "<script>alert(1)</script>",
                        "required": True,
                    }
                ]
            }
        )


def test_form_schema_validates_answers() -> None:
    schema = form_schema.validate_form_schema(
        {
            "fields": [
                {"key": "name", "type": "short_text", "label": "Name", "required": True},
                {"key": "agree", "type": "yes_no", "label": "Agree", "required": True},
            ]
        }
    )
    answers = form_schema.validate_answers(schema, {"name": "Ada", "agree": "yes"})
    assert answers["agree"] is True


@pytest.mark.postgres
def test_f213_cross_org_workflow_isolation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="WA", slug=f"wa-{unique_suffix}")
    org_b = Organisation(name="WB", slug=f"wb-{unique_suffix}")
    u_a = User(email=f"wa-{unique_suffix}@example.com", display_name="A", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add_all([org_a, org_b, u_a])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=u_a.id,
            organisation_id=org_a.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.commit()
    apply_organisation_rls(db_session, org_a.id)
    ctx_a = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, u_a.id)
    wf = workflows.create_workflow(
        db_session,
        ctx_a,
        WorkflowCreate(
            code="housing-default",
            name="Housing",
            process_type="housing_application",
            steps=[WorkflowStep(order=0, name="Review", reviewer_roles=["organisation_admin"])],
        ),
    )
    db_session.commit()
    apply_organisation_rls(db_session, org_b.id)
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, u_a.id)
    with pytest.raises(Exception):
        workflows.get_workflow(db_session, ctx_b, uuid.UUID(wf["id"]))
    db_session.rollback()


@pytest.mark.postgres
def test_f213_secure_sharing_revoke(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name="WS", slug=f"ws-{unique_suffix}")
    u = User(email=f"ws-{unique_suffix}@example.com", display_name="U", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add_all([org, u])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=u.id,
            organisation_id=org.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.commit()
    apply_organisation_rls(db_session, org.id)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, u.id)
    exp = datetime.now(timezone.utc) + timedelta(hours=24)
    created = sharing.create_grant(
        db_session,
        ctx,
        SharingGrantCreate(
            resource_type="housing_application",
            resource_id=uuid.uuid4(),
            recipient_user_id=u.id,
            purpose="Review",
            scope={"fields": ["summary"]},
            expires_at=exp,
        ),
    )
    token = created["access_token"]
    sharing.access_by_token(db_session, ctx, token)
    sharing.revoke_grant(db_session, ctx, uuid.UUID(created["id"]), None)
    with pytest.raises(Exception):
        sharing.access_by_token(db_session, ctx, token)
    db_session.rollback()
