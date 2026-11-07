"""F3.12 PostgreSQL tests. AI is not called; queries are ORM allowlist filters."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.complaints import Complaint
from app.db.models.enums import HMoreRole, MembershipStatus
from app.operational_search.service import clear_interpret_cache, search
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
def test_f312_search_is_org_scoped_and_assignment_filtered(
    db_session: Session, unique_suffix: str
) -> None:
    clear_interpret_cache()
    apply_platform_rls_bypass(db_session)
    org = Organisation(name=f"OS {unique_suffix}", slug=f"os-{unique_suffix}")
    other = Organisation(name=f"OT {unique_suffix}", slug=f"ot-{unique_suffix}")
    admin = User(email=f"a-{unique_suffix}@example.com", display_name="Admin", external_subject=f"auth0|{uuid.uuid4()}")
    worker = User(email=f"w-{unique_suffix}@example.com", display_name="SW", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add_all([org, other, admin, worker])
    db_session.flush()
    db_session.add_all(
        [
            OrganisationMembership(
                user_id=admin.id,
                organisation_id=org.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=worker.id,
                organisation_id=org.id,
                role=HMoreRole.SUPPORT_WORKER,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    now = datetime.now(timezone.utc)
    mine = Complaint(
        organisation_id=org.id,
        reference_number=f"C-{unique_suffix}-1",
        title="Open heating complaint",
        description="Heating",
        status="submitted",
        submitted_at=now,
        assigned_user_id=worker.id,
    )
    theirs = Complaint(
        organisation_id=org.id,
        reference_number=f"C-{unique_suffix}-2",
        title="Other open complaint",
        description="Other",
        status="submitted",
        submitted_at=now,
        assigned_user_id=admin.id,
    )
    foreign = Complaint(
        organisation_id=other.id,
        reference_number=f"C-{unique_suffix}-x",
        title="Other org complaint",
        description="Hidden",
        status="submitted",
        submitted_at=now,
    )
    closed = Complaint(
        organisation_id=org.id,
        reference_number=f"C-{unique_suffix}-3",
        title="Closed complaint",
        description="Done",
        status="closed",
        submitted_at=now,
        assigned_user_id=worker.id,
    )
    db_session.add_all([mine, theirs, foreign, closed])
    db_session.flush()
    apply_organisation_rls(db_session, org.id)

    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, worker.id)
    settings = Settings(ai_service_base_url="", ai_service_token="")

    admin_result = search(db_session, admin_ctx, "Show complaints that are still open", settings=settings)
    assert admin_result["executed_sql"] is False
    assert admin_result["outcome"] == "results"
    ids = {item["id"] for item in admin_result["items"]}
    assert str(mine.id) in ids
    assert str(theirs.id) in ids
    assert str(foreign.id) not in ids
    assert str(closed.id) not in ids

    clear_interpret_cache()
    worker_result = search(db_session, worker_ctx, "Show complaints that are still open", settings=settings)
    worker_ids = {item["id"] for item in worker_result["items"]}
    assert worker_ids == {str(mine.id)}

    outsider = User(
        email=f"o-{unique_suffix}@example.com",
        display_name="O",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add(outsider)
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=outsider.id,
            organisation_id=other.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()
    apply_organisation_rls(db_session, other.id)
    clear_interpret_cache()
    other_result = search(
        db_session,
        _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, outsider.id),
        "Show complaints that are still open",
        settings=settings,
    )
    other_ids = {item["id"] for item in other_result["items"]}
    assert str(foreign.id) in other_ids
    assert str(mine.id) not in other_ids
    assert str(theirs.id) not in other_ids
