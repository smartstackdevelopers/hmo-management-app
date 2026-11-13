"""F1.7 audit log framework tests.

Unit tests run offline. PostgreSQL-marked tests require DATABASE_URL / TEST_DATABASE_URL
and a migrated pgvector database. Skipped tests are not claimed as passed.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit.events import EMERGENCY_REQUESTED, TENANT_CREATE
from app.audit.query import get_audit_event_for_org, list_audit_events
from app.audit.redaction import REDACTED, sanitize_metadata, sanitize_reason
from app.audit.service import AuditOutcome, record_event
from app.db.models.enums import HMoreRole, MembershipStatus
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def test_audit_read_permission_matrix() -> None:
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.AUDIT_LOGS_READ)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.AUDIT_LOGS_READ)
    assert not role_has_permission(HMoreRole.TENANT, Permission.AUDIT_LOGS_READ)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.AUDIT_LOGS_READ)
    assert not role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.AUDIT_LOGS_READ)
    assert not role_has_permission(
        HMoreRole.MAINTENANCE_CONTRACTOR, Permission.AUDIT_LOGS_READ
    )


def test_sensitive_metadata_redaction() -> None:
    cleaned = sanitize_metadata(
        {
            "password": "secret",
            "access_token": "abc",
            "refresh_token": "xyz",
            "note": "ok",
            "nested": {"mfa_code": "123456", "safe": 1},
        }
    )
    assert cleaned["password"] == REDACTED
    assert cleaned["access_token"] == REDACTED
    assert cleaned["refresh_token"] == REDACTED
    assert cleaned["note"] == "ok"
    assert cleaned["nested"]["mfa_code"] == REDACTED
    assert cleaned["nested"]["safe"] == 1


def test_invalid_metadata_rejected() -> None:
    # Strings longer than 500 are truncated during redaction; still need many keys
    # to exceed the 4 KiB encoded metadata budget.
    oversized = {f"k{i}": "y" * 200 for i in range(40)}
    with pytest.raises(ValueError, match="metadata exceeds"):
        sanitize_metadata(oversized)
    with pytest.raises(ValueError, match="object"):
        sanitize_metadata(["not", "a", "dict"])  # type: ignore[arg-type]


def test_reason_bounds() -> None:
    assert sanitize_reason(" Break-glass review ") == "Break-glass review"
    with pytest.raises(ValueError):
        sanitize_reason("   ")
    with pytest.raises(ValueError):
        sanitize_reason("r" * 1001)


def test_unauthenticated_audit_api_returns_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/audit-events").status_code == 401
    assert client.get("/api/v1/audit-events/platform").status_code == 401
    assert client.post("/api/v1/emergency-access", json={"reason": "x"}).status_code == 401


def _org_ctx(role: HMoreRole, org_id: uuid.UUID | None = None) -> OrganisationContext:
    organisation_id = org_id or uuid.uuid4()
    user = SimpleNamespace(
        id=uuid.uuid4(),
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
                organisation_id=organisation_id,
                status=MembershipStatus.ACTIVE,
            )
        ],
        active_organisation_id=organisation_id,
        active_role=role,
    )
    return OrganisationContext(
        user=user,  # type: ignore[arg-type]
        organisation_id=organisation_id,
        role=role,
        authorization=authz,
    )


@pytest.mark.postgres
def test_audit_event_creation_attribution_and_outcomes(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, User
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Audit Org", slug=f"audit-{unique_suffix}")
    actor = User(
        email=f"audit-{unique_suffix}@example.com",
        display_name="Auditor",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, actor])
    db_session.flush()

    apply_organisation_rls(db_session, org.id)
    success = record_event(
        db_session,
        action=TENANT_CREATE,
        resource_type="tenant",
        resource_id=uuid.uuid4(),
        organisation_id=org.id,
        actor_user_id=actor.id,
        actor_role=HMoreRole.ORGANISATION_ADMIN.value,
        outcome=AuditOutcome.SUCCESS,
        correlation_id="corr-success",
        summary="tenant created",
        metadata={"preferred_name_length": 4},
    )
    denied = record_event(
        db_session,
        action="auth.access.denied",
        resource_type="permission",
        resource_id="tenants.manage",
        organisation_id=org.id,
        actor_user_id=actor.id,
        actor_role=HMoreRole.TENANT.value,
        outcome=AuditOutcome.DENIED,
        summary="denied",
    )
    failure = record_event(
        db_session,
        action="tenant.update",
        resource_type="tenant",
        organisation_id=org.id,
        actor_user_id=actor.id,
        outcome=AuditOutcome.FAILURE,
        summary="validation failed",
    )
    assert success is not None
    assert success.actor_user_id == actor.id
    assert success.organisation_id == org.id
    assert success.outcome == "success"
    assert success.actor_role == HMoreRole.ORGANISATION_ADMIN.value
    assert denied is not None and denied.outcome == "denied"
    assert failure is not None and failure.outcome == "failure"


@pytest.mark.postgres
def test_audit_redaction_persisted(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, User
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Redact Org", slug=f"redact-{unique_suffix}")
    actor = User(
        email=f"redact-{unique_suffix}@example.com",
        display_name="R",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, actor])
    db_session.flush()
    apply_organisation_rls(db_session, org.id)
    event = record_event(
        db_session,
        action="test.redact",
        resource_type="probe",
        organisation_id=org.id,
        actor_user_id=actor.id,
        metadata={"password": "nope", "ok": True},
    )
    assert event is not None
    assert event.metadata_json["password"] == REDACTED
    assert event.metadata_json["ok"] is True


@pytest.mark.postgres
def test_audit_pagination_filtering_and_org_isolation(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, User
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="A", slug=f"aa-{unique_suffix}")
    org_b = Organisation(name="B", slug=f"bb-{unique_suffix}")
    actor = User(
        email=f"page-{unique_suffix}@example.com",
        display_name="P",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, actor])
    db_session.flush()

    apply_organisation_rls(db_session, org_a.id)
    for i in range(3):
        record_event(
            db_session,
            action=TENANT_CREATE if i < 2 else "tenant.update",
            resource_type="tenant",
            resource_id=uuid.uuid4(),
            organisation_id=org_a.id,
            actor_user_id=actor.id,
            outcome=AuditOutcome.SUCCESS,
        )
    apply_organisation_rls(db_session, org_b.id)
    record_event(
        db_session,
        action=TENANT_CREATE,
        resource_type="tenant",
        resource_id=uuid.uuid4(),
        organisation_id=org_b.id,
        actor_user_id=actor.id,
        outcome=AuditOutcome.SUCCESS,
    )

    apply_organisation_rls(db_session, org_a.id)
    rows, total = list_audit_events(
        db_session,
        organisation_id=org_a.id,
        page=1,
        page_size=2,
        action=TENANT_CREATE,
    )
    assert total == 2
    assert len(rows) == 2
    assert all(row.organisation_id == org_a.id for row in rows)

    foreign = get_audit_event_for_org(db_session, org_a.id, rows[0].id)
    assert foreign is not None
    # Cross-org: even if we know B's event id, org A helper returns None
    apply_platform_rls_bypass(db_session)
    b_rows, _ = list_audit_events(
        db_session, organisation_id=org_b.id, page=1, page_size=10
    )
    assert len(b_rows) >= 1
    assert get_audit_event_for_org(db_session, org_a.id, b_rows[0].id) is None


@pytest.mark.postgres
def test_audit_rows_append_only_for_app_role(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, User
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Append", slug=f"append-{unique_suffix}")
    actor = User(
        email=f"append-{unique_suffix}@example.com",
        display_name="A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, actor])
    db_session.flush()
    apply_organisation_rls(db_session, org.id)
    event = record_event(
        db_session,
        action="test.append",
        resource_type="probe",
        organisation_id=org.id,
        actor_user_id=actor.id,
    )
    assert event is not None
    nested = db_session.begin_nested()
    try:
        db_session.execute(
            text("UPDATE audit_events SET summary = 'tamper' WHERE id = :id"),
            {"id": str(event.id)},
        )
        db_session.flush()
        pytest.fail("expected UPDATE to be denied for hmore_app")
    except Exception:
        nested.rollback()
    nested = db_session.begin_nested()
    try:
        db_session.execute(
            text("DELETE FROM audit_events WHERE id = :id"),
            {"id": str(event.id)},
        )
        db_session.flush()
        pytest.fail("expected DELETE to be denied for hmore_app")
    except Exception:
        nested.rollback()


@pytest.mark.postgres
def test_emergency_access_logging_does_not_grant_permissions(
    db_session, unique_suffix: str
) -> None:
    from app.audit.emergency import request_emergency_access, transition_emergency_access
    from app.db.models import Organisation, OrganisationMembership, User
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Emerg", slug=f"emerg-{unique_suffix}")
    actor = User(
        email=f"emerg-{unique_suffix}@example.com",
        display_name="E",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, actor])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=actor.id,
            organisation_id=org.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    db_session.flush()

    ctx = _org_ctx(HMoreRole.ORGANISATION_ADMIN, org.id)
    ctx.user.id = actor.id  # type: ignore[attr-defined]
    ctx.authorization.user.id = actor.id  # type: ignore[attr-defined]

    apply_organisation_rls(db_session, org.id)
    grant = request_emergency_access(
        db_session,
        ctx,
        reason="Suspected data integrity incident",
        duration_hours=2,
        resource_type="tenant",
        resource_id=str(uuid.uuid4()),
    )
    assert grant.status == "requested"
    # Recording does not elevate RBAC (no platform permissions granted by the event)
    assert not role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.PLATFORM_SETTINGS_MANAGE)

    transition_emergency_access(db_session, ctx, grant.id, new_status="approved")
    transition_emergency_access(db_session, ctx, grant.id, new_status="active")
    transition_emergency_access(db_session, ctx, grant.id, new_status="revoked")

    rows, total = list_audit_events(
        db_session,
        organisation_id=org.id,
        page=1,
        page_size=20,
        resource_type="emergency_access",
    )
    assert total >= 4
    actions = {row.action for row in rows}
    assert EMERGENCY_REQUESTED in actions
    assert "emergency_access.approved" in actions
    assert "emergency_access.activated" in actions
    assert "emergency_access.revoked" in actions


@pytest.mark.postgres
def test_recursive_audit_guard(db_session, unique_suffix: str, monkeypatch) -> None:
    from app.audit import service as audit_service
    from app.db.models import Organisation, User
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Recurse", slug=f"rec-{unique_suffix}")
    actor = User(
        email=f"rec-{unique_suffix}@example.com",
        display_name="R",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, actor])
    db_session.flush()
    apply_organisation_rls(db_session, org.id)

    audit_service._RECORDING = True
    try:
        result = record_event(
            db_session,
            action="should.skip",
            resource_type="probe",
            organisation_id=org.id,
            actor_user_id=actor.id,
        )
        assert result is None
    finally:
        audit_service._RECORDING = False

