"""F2.12 communication platform — PostgreSQL-backed tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.communication import service as comm_service
from app.communication.schemas import MessageSend, OperationalSend
from app.db.models import (
    CommunicationDelivery,
    CommunicationMessage,
    Organisation,
    OrganisationMembership,
    User,
)
from app.db.models.enums import HMoreRole, MembershipStatus
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass
from app.workers.celery_app import celery_app


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


@pytest.mark.postgres
def test_f212_cross_org_message_isolation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="CA", slug=f"ca-{unique_suffix}")
    org_b = Organisation(name="CB", slug=f"cb-{unique_suffix}")
    u_a = User(email=f"a-{unique_suffix}@example.com", display_name="A", external_subject=f"auth0|{uuid.uuid4()}")
    u_b = User(email=f"b-{unique_suffix}@example.com", display_name="B", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add_all([org_a, org_b, u_a, u_b])
    db_session.flush()
    db_session.add_all(
        [
            OrganisationMembership(
                user_id=u_a.id,
                organisation_id=org_a.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=u_b.id,
                organisation_id=org_b.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()

    conv = uuid.uuid4()
    msg = CommunicationMessage(
        organisation_id=org_a.id,
        conversation_id=conv,
        sender_user_id=u_a.id,
        subject="S",
        body="B",
        message_type="direct",
    )
    db_session.add(msg)
    db_session.flush()

    apply_organisation_rls(db_session, org_b.id)
    rows = list(db_session.scalars(select(CommunicationMessage)).all())
    assert rows == []

    apply_platform_rls_bypass(db_session)
    rows2 = list(db_session.scalars(select(CommunicationMessage)).all())
    assert len(rows2) == 1


@pytest.mark.postgres
def test_f212_operational_send_idempotent(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name="CX", slug=f"cx-{unique_suffix}")
    admin = User(email=f"adm-{unique_suffix}@example.com", display_name="Ad", external_subject=f"auth0|{uuid.uuid4()}")
    rec = User(
        email=f"rec-{unique_suffix}@example.com",
        display_name="R",
        external_subject=f"auth0|{uuid.uuid4()}",
        phone="+441234567890",
    )
    db_session.add_all([org, admin, rec])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=admin.id,
            organisation_id=org.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.add(
        OrganisationMembership(
            user_id=rec.id,
            organisation_id=org.id,
            role=HMoreRole.TENANT,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()

    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    apply_organisation_rls(db_session, org.id)

    body = OperationalSend(
        recipient_user_id=rec.id,
        channel="email",
        subject="Hello",
        body="Test body",
        essential_operational=True,
    )
    r1 = comm_service.operational_send(db_session, ctx, body)
    r2 = comm_service.operational_send(db_session, ctx, body)
    assert r1["delivery_id"] == r2["delivery_id"]
    assert r2.get("deduplicated") is True


def test_celery_f212_task_registered() -> None:
    assert "hmore.communication.dispatch_scheduled_reminders" in celery_app.tasks
