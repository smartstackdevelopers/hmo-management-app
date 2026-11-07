"""F3.11 PostgreSQL integration tests. Search-based only — no AI provider calls."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.audit import AuditEvent
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.db.models.file_metadata import FileMetadata
from app.db.models.housing import HousingApplication
from app.db.models.tenant import Tenant
from app.duplicate_detection import service as dd_service
from app.duplicate_detection.matching import detect_tenant_duplicates
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
    return OrganisationContext(user=user, organisation_id=org_id, role=role, authorization=authz)  # type: ignore[arg-type]


def _seed(session: Session, suffix: str):
    org = Organisation(name=f"DD {suffix}", slug=f"dd-{suffix}")
    other = Organisation(name=f"DX {suffix}", slug=f"dx-{suffix}")
    admin = User(email=f"a-{suffix}@example.com", display_name="Admin", external_subject=f"auth0|{uuid.uuid4()}")
    worker = User(email=f"w-{suffix}@example.com", display_name="SW", external_subject=f"auth0|{uuid.uuid4()}")
    session.add_all([org, other, admin, worker])
    session.flush()
    session.add_all(
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
    session.flush()
    return org, other, admin, worker


@pytest.mark.postgres
def test_f311_detects_email_duplicates_without_ai_or_mutation(
    db_session: Session, unique_suffix: str
) -> None:
    apply_platform_rls_bypass(db_session)
    org, other, admin, worker = _seed(db_session, unique_suffix)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, worker.id)
    apply_organisation_rls(db_session, org.id)

    t1 = Tenant(
        organisation_id=org.id,
        preferred_name="Alice One",
        email=f"Alice.{unique_suffix}@Example.COM",
        phone="+44 7700 900111",
        status=RecordStatus.ACTIVE,
    )
    t2 = Tenant(
        organisation_id=org.id,
        preferred_name="Alice Two",
        email=f"alice.{unique_suffix}@example.com",
        phone="+44 7700 900222",
        status=RecordStatus.ACTIVE,
    )
    # Name-similar only — must not become exact/strong alone.
    t3 = Tenant(
        organisation_id=org.id,
        preferred_name="Alice Onne",
        email=f"other-{unique_suffix}@example.com",
        status=RecordStatus.ACTIVE,
    )
    # Cross-org twin must never appear.
    t_other = Tenant(
        organisation_id=other.id,
        preferred_name="Alice One",
        email=f"alice.{unique_suffix}@example.com",
        status=RecordStatus.ACTIVE,
    )
    db_session.add_all([t1, t2, t3, t_other])
    db_session.flush()
    before_ids = {t1.id, t2.id, t3.id}

    result = dd_service.run_detection(
        db_session, admin_ctx, record_types=["tenant"], trigger="manual"
    )
    assert result["used_ai"] is False
    assert "Potential Duplicates" in result["notice"]
    assert result["findings_created"] >= 1
    email_hits = [
        item
        for item in result["findings"]
        if "email" in (item.get("matching_fields") or [])
    ]
    assert email_hits
    assert all(item["match_strength"] == "exact" for item in email_hits)
    assert all(item["identity_proven"] is False for item in email_hits)
    assert all(item["auto_merged"] is False for item in email_hits)
    assert all(item["auto_deleted"] is False for item in email_hits)

    name_only = [
        item
        for item in result["findings"]
        if item.get("matching_fields") == ["preferred_name"]
    ]
    for item in name_only:
        assert item["match_strength"] == "possible"

    # Source records unchanged
    for tid in before_ids:
        row = db_session.get(Tenant, tid)
        assert row is not None
        assert row.status == RecordStatus.ACTIVE

    with pytest.raises(HTTPException) as denied:
        dd_service.run_detection(db_session, worker_ctx, record_types=["tenant"])
    assert denied.value.status_code == 403

    finding_id = uuid.UUID(email_hits[0]["id"])
    with pytest.raises(HTTPException) as review_denied:
        dd_service.review_finding(
            db_session, worker_ctx, finding_id, decision="confirm", review_comment=None
        )
    assert review_denied.value.status_code == 403

    reviewed = dd_service.review_finding(
        db_session, admin_ctx, finding_id, decision="confirm", review_comment="Checked"
    )
    assert reviewed["review_status"] == "confirmed_duplicate"
    for tid in before_ids:
        assert db_session.get(Tenant, tid).status == RecordStatus.ACTIVE

    again = dd_service.run_detection(db_session, admin_ctx, record_types=["tenant"])
    assert again["findings_deduplicated"] >= 1

    outsider = User(
        email=f"o-{unique_suffix}@example.com",
        display_name="O",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add(outsider)
    db_session.flush()
    with pytest.raises(HTTPException) as hidden:
        dd_service.get_run(
            db_session,
            _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, outsider.id),
            uuid.UUID(result["id"]),
        )
    assert hidden.value.status_code in {403, 404}

    actions = set(
        db_session.scalars(select(AuditEvent.action).where(AuditEvent.organisation_id == org.id)).all()
    )
    assert audit_events.DUPLICATE_DETECTION_REQUESTED in actions
    assert audit_events.DUPLICATE_DETECTION_COMPLETED in actions
    assert audit_events.DUPLICATE_DETECTION_CONFIRMED in actions


@pytest.mark.postgres
def test_f311_housing_and_file_duplicates_and_dismiss_sticky(
    db_session: Session, unique_suffix: str
) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, admin, _worker = _seed(db_session, unique_suffix)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    apply_organisation_rls(db_session, org.id)

    tenant = Tenant(
        organisation_id=org.id,
        preferred_name="Pat",
        status=RecordStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.flush()
    app1 = HousingApplication(
        organisation_id=org.id,
        reference_number=f"HA-{unique_suffix}-1",
        tenant_id=tenant.id,
        created_by_user_id=admin.id,
        housing_requirements="Accessible flat",
        status="submitted",
    )
    app2 = HousingApplication(
        organisation_id=org.id,
        reference_number=f"HA-{unique_suffix}-2",
        tenant_id=tenant.id,
        created_by_user_id=admin.id,
        housing_requirements="Accessible flat near transport",
        status="under_review",
    )
    checksum = "a" * 64
    f1 = FileMetadata(
        organisation_id=org.id,
        storage_key=f"dd/{unique_suffix}/1.pdf",
        original_filename="proof.pdf",
        content_type="application/pdf",
        size_bytes=100,
        checksum_sha256=checksum,
        status="active",
        uploaded_by_user_id=admin.id,
    )
    f2 = FileMetadata(
        organisation_id=org.id,
        storage_key=f"dd/{unique_suffix}/2.pdf",
        original_filename="proof.pdf",
        content_type="application/pdf",
        size_bytes=100,
        checksum_sha256=checksum,
        status="active",
        uploaded_by_user_id=admin.id,
    )
    db_session.add_all([app1, app2, f1, f2])
    db_session.flush()

    result = dd_service.run_detection(
        db_session,
        admin_ctx,
        record_types=["housing_application", "file_metadata"],
    )
    assert result["used_ai"] is False
    types = {item["record_type"] for item in result["findings"]}
    assert "housing_application" in types
    assert "file_metadata" in types

    file_hit = next(item for item in result["findings"] if item["record_type"] == "file_metadata")
    dismissed = dd_service.review_finding(
        db_session,
        admin_ctx,
        uuid.UUID(file_hit["id"]),
        decision="dismiss",
        review_comment="Different uploads intentional",
    )
    assert dismissed["review_status"] == "not_duplicate"

    again = dd_service.run_detection(
        db_session, admin_ctx, record_types=["file_metadata"]
    )
    assert again["findings_created"] == 0
    assert again["findings_deduplicated"] >= 1
    assert db_session.get(FileMetadata, f1.id).status == "active"
    assert db_session.get(FileMetadata, f2.id).status == "active"
    assert db_session.get(HousingApplication, app1.id).status == "submitted"


@pytest.mark.postgres
def test_f311_record_scoped_detection_limits_candidates(
    db_session: Session, unique_suffix: str
) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, admin, _worker = _seed(db_session, unique_suffix)
    apply_organisation_rls(db_session, org.id)
    source = Tenant(
        organisation_id=org.id,
        preferred_name="Source",
        email=f"source-{unique_suffix}@example.com",
        tenancy_reference=f"REF-{unique_suffix}",
        status=RecordStatus.ACTIVE,
    )
    twin = Tenant(
        organisation_id=org.id,
        preferred_name="Twin",
        email=f"source-{unique_suffix}@example.com",
        tenancy_reference=f"ref-{unique_suffix}",
        status=RecordStatus.ACTIVE,
    )
    unrelated = Tenant(
        organisation_id=org.id,
        preferred_name="Unrelated",
        email=f"unrelated-{unique_suffix}@example.com",
        status=RecordStatus.ACTIVE,
    )
    db_session.add_all([source, twin, unrelated])
    db_session.flush()

    scanned, compared, hits = detect_tenant_duplicates(
        db_session, org.id, source_id=source.id, limit_pairs=50
    )
    assert scanned >= 2
    assert compared >= 1
    assert any(hit.match_strength == "exact" for hit in hits)
    assert all(unrelated.id not in (hit.source_id, hit.candidate_id) for hit in hits)
