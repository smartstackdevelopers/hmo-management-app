"""F2.6 evidence checklist, review workflow, pack generation, isolation tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.evidence.pdf import build_simple_pdf
from app.evidence.service import EVIDENCE_TRANSITIONS
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def test_f26_permissions() -> None:
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.EVIDENCE_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.EVIDENCE_REVIEW)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.EVIDENCE_PACK_GENERATE)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.EVIDENCE_MANAGE_ASSIGNED)
    assert role_has_permission(HMoreRole.SUPPORT_WORKER, Permission.EVIDENCE_READ_ASSIGNED)
    assert role_has_permission(HMoreRole.TENANT, Permission.EVIDENCE_READ_OWN)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.EVIDENCE_MANAGE)
    assert not role_has_permission(HMoreRole.MAINTENANCE_CONTRACTOR, Permission.EVIDENCE_READ_OWN)
    assert not role_has_permission(HMoreRole.TENANT, Permission.EVIDENCE_PACK_GENERATE)


def test_evidence_transitions() -> None:
    assert "received" in EVIDENCE_TRANSITIONS["pending"]
    assert "accepted" not in EVIDENCE_TRANSITIONS["pending"]
    assert "accepted" in EVIDENCE_TRANSITIONS["under_review"]
    assert "rejected" in EVIDENCE_TRANSITIONS["under_review"]


def test_pdf_builder_produces_pdf_header() -> None:
    pdf = build_simple_pdf("Evidence Pack APP-1", ["Line one", "Missing: proof of address"])
    assert pdf.startswith(b"%PDF-1.4")
    assert b"Evidence Pack APP-1" in pdf
    assert b"Missing: proof of address" in pdf


def test_unauthenticated_evidence_apis_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/evidence-templates").status_code == 401
    fake = uuid.uuid4()
    assert client.get(f"/api/v1/housing-applications/{fake}/evidence").status_code == 401
    assert client.get(f"/api/v1/evidence-packs/{fake}/download").status_code == 401


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
def test_evidence_checklist_review_pack_and_isolation(
    db_session, unique_suffix: str
) -> None:
    from app.db.models import Organisation, OrganisationMembership, Tenant, User
    from app.db.models.audit import AuditEvent
    from app.evidence import service as evidence_service
    from app.evidence.schemas import (
        AssociateFileRequest,
        ChecklistItemCreate,
        ChecklistItemUpdate,
        GeneratePackRequest,
    )
    from app.housing import service as housing_service
    from app.housing.schemas import ApplicationCreate
    from app.storage.factory import reset_storage_backend_cache
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass
    from sqlalchemy import select

    reset_storage_backend_cache()

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Evidence Org", slug=f"ev-{unique_suffix}")
    other = Organisation(name="Other Org", slug=f"ev-o-{unique_suffix}")
    admin = User(
        email=f"oa-ev-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    other_admin = User(
        email=f"oa2-ev-{unique_suffix}@example.com",
        display_name="Other",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, other, admin, other_admin])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id,
        preferred_name="Applicant",
        status=RecordStatus.ACTIVE,
    )
    db_session.add(tenant)
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
                user_id=other_admin.id,
                organisation_id=other.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()
    apply_organisation_rls(db_session, org.id)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)

    application = housing_service.create_application(
        db_session,
        admin_ctx,
        ApplicationCreate(
            tenant_id=tenant.id,
            housing_requirements="Need supported housing",
            priority="normal",
            submit=True,
        ),
    )

    seeded = evidence_service.seed_checklist_from_templates(db_session, admin_ctx, application.id)
    assert len(seeded) >= 1
    items = evidence_service.list_checklist(db_session, admin_ctx, application.id)
    assert items

    item = evidence_service.create_checklist_item(
        db_session,
        admin_ctx,
        application.id,
        ChecklistItemCreate(title="Bank statement", category="finance", is_required=True),
    )
    assert item.status == "pending"

    # Invalid transition
    with pytest.raises(HTTPException) as bad_transition:
        evidence_service.update_checklist_item(
            db_session,
            admin_ctx,
            item.id,
            ChecklistItemUpdate(status="accepted"),
        )
    assert bad_transition.value.status_code == 400

    evidence_service.update_checklist_item(
        db_session,
        admin_ctx,
        item.id,
        ChecklistItemUpdate(status="received"),
    )
    evidence_service.update_checklist_item(
        db_session,
        admin_ctx,
        item.id,
        ChecklistItemUpdate(status="under_review"),
    )

    # Rejection requires reason
    with pytest.raises(HTTPException) as no_reason:
        evidence_service.update_checklist_item(
            db_session,
            admin_ctx,
            item.id,
            ChecklistItemUpdate(status="rejected"),
        )
    assert no_reason.value.status_code == 400

    evidence_service.update_checklist_item(
        db_session,
        admin_ctx,
        item.id,
        ChecklistItemUpdate(status="rejected", rejection_reason="Illegible scan"),
    )
    history = evidence_service.list_review_history(db_session, admin_ctx, item.id)
    assert any(h.to_status == "rejected" for h in history)

    # Move back and accept with file
    evidence_service.update_checklist_item(
        db_session,
        admin_ctx,
        item.id,
        ChecklistItemUpdate(status="received"),
    )
    uploaded = evidence_service.upload_and_associate(
        db_session,
        admin_ctx,
        item.id,
        filename="statement.pdf",
        content_type="application/pdf",
        data=b"%PDF-1.4 fake-evidence",
    )
    assert uploaded.status == "received"
    out = evidence_service.item_out_dict(db_session, uploaded)
    assert len(out["file_ids"]) >= 1

    evidence_service.update_checklist_item(
        db_session,
        admin_ctx,
        item.id,
        ChecklistItemUpdate(status="under_review"),
    )
    evidence_service.update_checklist_item(
        db_session,
        admin_ctx,
        item.id,
        ChecklistItemUpdate(status="accepted"),
    )

    # Accept all required seeded items that are still outstanding
    for row in evidence_service.list_checklist(db_session, admin_ctx, application.id):
        if row.is_required and row.status not in {"accepted", "not_applicable"}:
            if row.status == "pending":
                evidence_service.update_checklist_item(
                    db_session, admin_ctx, row.id, ChecklistItemUpdate(status="received")
                )
            current = evidence_service.get_checklist_item(db_session, admin_ctx, row.id)
            if current.status == "received":
                evidence_service.update_checklist_item(
                    db_session, admin_ctx, row.id, ChecklistItemUpdate(status="under_review")
                )
            current = evidence_service.get_checklist_item(db_session, admin_ctx, row.id)
            if current.status == "under_review":
                evidence_service.update_checklist_item(
                    db_session, admin_ctx, row.id, ChecklistItemUpdate(status="accepted")
                )

    ready = evidence_service.readiness(db_session, admin_ctx, application.id)
    assert ready["is_complete"] is True

    # Incomplete generation blocked when allow_incomplete=False on a fresh incomplete item
    incomplete_item = evidence_service.create_checklist_item(
        db_session,
        admin_ctx,
        application.id,
        ChecklistItemCreate(title="Extra required", category="general", is_required=True),
    )
    with pytest.raises(HTTPException) as incomplete:
        evidence_service.generate_pack(
            db_session, admin_ctx, application.id, GeneratePackRequest(allow_incomplete=False)
        )
    assert incomplete.value.status_code == 400

    draft = evidence_service.generate_pack(
        db_session, admin_ctx, application.id, GeneratePackRequest(allow_incomplete=True)
    )
    assert draft.is_complete is False
    assert draft.status == "incomplete_draft"
    assert draft.file_id is not None

    evidence_service.update_checklist_item(
        db_session,
        admin_ctx,
        incomplete_item.id,
        ChecklistItemUpdate(status="not_applicable"),
    )
    complete_pack = evidence_service.generate_pack(
        db_session, admin_ctx, application.id, GeneratePackRequest(allow_incomplete=False)
    )
    assert complete_pack.is_complete is True
    _pack, content, content_type, _name = evidence_service.download_pack_bytes(
        db_session, admin_ctx, complete_pack.id
    )
    assert content.startswith(b"%PDF")
    assert content_type == "application/pdf"

    audits = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.organisation_id == org.id,
            AuditEvent.action.in_(
                [
                    "evidence.checklist_seed",
                    "evidence.item_create",
                    "evidence.item_review",
                    "evidence.file_associate",
                    "evidence.pack_generate",
                    "evidence.pack_download",
                ]
            ),
        )
    ).all()
    assert len(audits) >= 4

    # Cross-organisation denial
    apply_organisation_rls(db_session, other.id)
    other_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, other_admin.id)
    with pytest.raises(HTTPException) as iso_list:
        evidence_service.list_checklist(db_session, other_ctx, application.id)
    assert iso_list.value.status_code == 404
    with pytest.raises(HTTPException) as iso_item:
        evidence_service.get_checklist_item(db_session, other_ctx, item.id)
    assert iso_item.value.status_code == 404
    with pytest.raises(HTTPException) as iso_pack:
        evidence_service.get_pack(db_session, other_ctx, complete_pack.id)
    assert iso_pack.value.status_code == 404
    with pytest.raises(HTTPException) as iso_gen:
        evidence_service.generate_pack(
            db_session, other_ctx, application.id, GeneratePackRequest(allow_incomplete=True)
        )
    assert iso_gen.value.status_code == 404

    # Invalid file association
    apply_organisation_rls(db_session, org.id)
    with pytest.raises(HTTPException) as bad_file:
        evidence_service.associate_file(
            db_session,
            admin_ctx,
            item.id,
            AssociateFileRequest(file_id=uuid.uuid4()),
        )
    assert bad_file.value.status_code == 404


@pytest.mark.postgres
def test_evidence_rbac_denies_maintenance(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, OrganisationMembership, Tenant, User
    from app.evidence import service as evidence_service
    from app.housing import service as housing_service
    from app.housing.schemas import ApplicationCreate
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="Ev RBAC", slug=f"ev-r-{unique_suffix}")
    admin = User(
        email=f"oa-r-{unique_suffix}@example.com",
        display_name="Admin",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    maint = User(
        email=f"mc-r-{unique_suffix}@example.com",
        display_name="Maint",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, admin, maint])
    db_session.flush()
    tenant = Tenant(
        organisation_id=org.id, preferred_name="T", status=RecordStatus.ACTIVE
    )
    db_session.add(tenant)
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
                user_id=maint.id,
                organisation_id=org.id,
                role=HMoreRole.MAINTENANCE_CONTRACTOR,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()
    apply_organisation_rls(db_session, org.id)
    admin_ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    maint_ctx = _ctx(HMoreRole.MAINTENANCE_CONTRACTOR, org.id, maint.id)
    application = housing_service.create_application(
        db_session,
        admin_ctx,
        ApplicationCreate(
            tenant_id=tenant.id,
            housing_requirements="Need room",
            priority="low",
            submit=False,
        ),
    )
    with pytest.raises(HTTPException) as denied:
        evidence_service.list_checklist(db_session, maint_ctx, application.id)
    assert denied.value.status_code == 403

