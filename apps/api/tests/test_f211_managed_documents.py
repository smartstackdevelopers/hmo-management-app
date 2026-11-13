"""F2.11 managed documents — isolation, reminders, signature gating (PostgreSQL)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.events import DOCUMENT_EXPIRY_REMINDER_DISPATCHED
from app.db.models import (
    AuditEvent,
    ManagedDocument,
    ManagedDocumentCategory,
    ManagedDocumentReminderLog,
    Organisation,
    OrganisationDocumentSettings,
    OrganisationMembership,
    ReminderRecord,
    User,
)
from app.db.models.enums import HMoreRole, MembershipStatus
from app.managed_documents.jobs import scan_and_schedule_document_reminders
from app.managed_documents.schemas import (
    DocumentCreate,
    SignatureConsent,
    SignatureRequestCreate,
    VersionCreateMeta,
    SIGN_ACK_PHRASE,
)
from app.managed_documents import service as md_service
from app.ops.reminders import dispatch_due_reminders
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


@pytest.mark.postgres
def test_f211_cross_org_isolation(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)

    org_a = Organisation(name="DMA", slug=f"dma-{unique_suffix}")
    org_b = Organisation(name="DMB", slug=f"dmb-{unique_suffix}")
    admin_a = User(
        email=f"doc-a-{unique_suffix}@example.com",
        display_name="A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    admin_b = User(
        email=f"doc-b-{unique_suffix}@example.com",
        display_name="B",
        external_subject=f"auth0|{uuid.uuid4()}",
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

    cat_a = ManagedDocumentCategory(
        organisation_id=org_a.id,
        code="general",
        title="General",
        access_classification="standard",
        sort_order=1,
    )
    cat_b = ManagedDocumentCategory(
        organisation_id=org_b.id,
        code="general",
        title="General",
        access_classification="standard",
        sort_order=1,
    )
    db_session.add_all([cat_a, cat_b])
    db_session.flush()

    ctx_a = _ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id, admin_a.id)
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id, admin_b.id)

    apply_organisation_rls(db_session, org_a.id)
    d_a = md_service.create_document_with_file(
        db_session,
        ctx_a,
        DocumentCreate(title="Lease A", category_id=cat_a.id, links=[]),
        filename="a.pdf",
        content_type="application/pdf",
        data=b"%PDF-1.4 a",
    )

    apply_organisation_rls(db_session, org_b.id)
    with pytest.raises(HTTPException) as denied:
        md_service.get_document(db_session, ctx_b, uuid.UUID(d_a["id"]))
    assert denied.value.status_code == 404


@pytest.mark.postgres
def test_f211_reminder_scan_idempotent_and_dispatch_writes_log(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name="DMR", slug=f"dmr-{unique_suffix}")
    user = User(
        email=f"dmr-{unique_suffix}@example.com",
        display_name="U",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, user])
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=user.id,
            organisation_id=org.id,
            role=HMoreRole.ORGANISATION_ADMIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    cat = ManagedDocumentCategory(
        organisation_id=org.id,
        code="general",
        title="General",
        access_classification="standard",
        sort_order=1,
    )
    db_session.add(cat)
    db_session.flush()

    db_session.add(
        OrganisationDocumentSettings(
            organisation_id=org.id,
            expiry_reminder_days_first=30,
            expiry_reminder_days_urgent=7,
        )
    )
    db_session.flush()

    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, user.id)
    apply_organisation_rls(db_session, org.id)

    created = md_service.create_document_with_file(
        db_session,
        ctx,
        DocumentCreate(
            title="Expiring",
            category_id=cat.id,
            expiry_date=date.today() + timedelta(days=5),
            links=[],
        ),
        filename="x.pdf",
        content_type="application/pdf",
        data=b"%PDF-1.4 x",
    )
    doc_id = uuid.UUID(created["id"])

    apply_platform_rls_bypass(db_session)
    first = scan_and_schedule_document_reminders(db_session)
    second = scan_and_schedule_document_reminders(db_session)
    assert first["scheduled"] >= 1
    assert second["scheduled"] == 0

    rem = db_session.scalar(
        select(ReminderRecord).where(
            ReminderRecord.organisation_id == org.id,
            ReminderRecord.resource_type == "managed_document",
            ReminderRecord.resource_id == doc_id,
        )
    )
    assert rem is not None
    rem.scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.flush()

    apply_platform_rls_bypass(db_session)
    dispatch_due_reminders(db_session, limit=50)

    logs = list(
        db_session.scalars(
            select(ManagedDocumentReminderLog).where(ManagedDocumentReminderLog.document_id == doc_id)
        )
    )
    assert len(logs) >= 1

    audit = list(
        db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.action == DOCUMENT_EXPIRY_REMINDER_DISPATCHED,
                AuditEvent.resource_id == str(doc_id),
            )
        )
    )
    assert len(audit) >= 1


@pytest.mark.postgres
def test_f211_signature_blocks_new_version_until_complete(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org = Organisation(name="DMS", slug=f"dms-{unique_suffix}")
    admin_a = User(
        email=f"dms-a-{unique_suffix}@example.com",
        display_name="A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    admin_b = User(
        email=f"dms-b-{unique_suffix}@example.com",
        display_name="B",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, admin_a, admin_b])
    db_session.flush()
    db_session.add_all(
        [
            OrganisationMembership(
                user_id=admin_a.id,
                organisation_id=org.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=admin_b.id,
                organisation_id=org.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    cat = ManagedDocumentCategory(
        organisation_id=org.id,
        code="general",
        title="General",
        access_classification="standard",
        sort_order=1,
    )
    db_session.add(cat)
    db_session.flush()

    ctx_a = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin_a.id)
    ctx_b = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin_b.id)
    apply_organisation_rls(db_session, org.id)

    doc = md_service.create_document_with_file(
        db_session,
        ctx_a,
        DocumentCreate(title="Sign me", category_id=cat.id, links=[]),
        filename="v1.pdf",
        content_type="application/pdf",
        data=b"%PDF-1.4 v1",
    )
    doc_id = uuid.UUID(doc["id"])
    v1_id = uuid.UUID(doc["current_version_id"])

    sig = md_service.create_signature_request(
        db_session,
        ctx_a,
        doc_id,
        SignatureRequestCreate(version_id=v1_id, signer_user_id=admin_b.id),
    )
    sig_id = uuid.UUID(sig["id"])

    with pytest.raises(HTTPException) as blocked:
        md_service.add_version(
            db_session,
            ctx_a,
            doc_id,
            filename="v2.pdf",
            content_type="application/pdf",
            data=b"%PDF-1.4 v2",
            meta=VersionCreateMeta(change_description="v2"),
        )
    assert blocked.value.status_code == 409

    done = md_service.complete_signature(
        db_session,
        ctx_b,
        sig_id,
        SignatureConsent(consent_text="I agree", acknowledgement=SIGN_ACK_PHRASE),
    )
    assert done["status"] == "signed"

    v2 = md_service.add_version(
        db_session,
        ctx_a,
        doc_id,
        filename="v2.pdf",
        content_type="application/pdf",
        data=b"%PDF-1.4 v2",
        meta=VersionCreateMeta(change_description="v2"),
    )
    assert v2["version_number"] == 2

    d = db_session.get(ManagedDocument, doc_id)
    assert d is not None
    assert d.current_version_id == uuid.UUID(v2["version_id"])

