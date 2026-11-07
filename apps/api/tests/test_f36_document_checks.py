"""F3.6 PostgreSQL tests. Extraction is local. AI calls are monkeypatched."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.core.config import Settings
from app.db.models import Organisation, OrganisationMembership, User
from app.db.models.audit import AuditEvent
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.managed_documents import ManagedDocument, ManagedDocumentCategory
from app.document_checks import service as check_service
from app.evidence.pdf import build_simple_pdf
from app.managed_documents import service as md_service
from app.managed_documents.schemas import DocumentCreate
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def _settings(**kwargs) -> Settings:
    base = dict(environment="test", ai_service_base_url="", ai_service_token="", storage_provider="memory")
    base.update(kwargs)
    return Settings(**base)


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
    org = Organisation(name=f"DC {suffix}", slug=f"dc-{suffix}")
    other = Organisation(name=f"DD {suffix}", slug=f"dd-{suffix}")
    admin = User(email=f"a-{suffix}@example.com", display_name="Admin", external_subject=f"auth0|{uuid.uuid4()}")
    worker = User(email=f"w-{suffix}@example.com", display_name="SW", external_subject=f"auth0|{uuid.uuid4()}")
    session.add_all([org, other, admin, worker])
    session.flush()
    session.add_all(
        [
            OrganisationMembership(
                user_id=admin.id, organisation_id=org.id, role=HMoreRole.ORGANISATION_ADMIN, status=MembershipStatus.ACTIVE
            ),
            OrganisationMembership(
                user_id=worker.id, organisation_id=org.id, role=HMoreRole.SUPPORT_WORKER, status=MembershipStatus.ACTIVE
            ),
        ]
    )
    category = ManagedDocumentCategory(
        organisation_id=org.id, code="general", title="General", access_classification="standard", sort_order=1
    )
    session.add(category)
    session.flush()
    return org, other, admin, worker, category


@pytest.mark.postgres
def test_f36_pdf_check_review_and_reprocess(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, admin, worker, category = _seed(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    apply_organisation_rls(db_session, org.id)
    created = md_service.create_document_with_file(
        db_session,
        ctx,
        DocumentCreate(title="Agreement", category_id=category.id, links=[]),
        filename="agreement.pdf",
        content_type="application/pdf",
        data=build_simple_pdf("Tenancy agreement excerpt", ["Reference T-100 is recorded on this page."]),
    )
    doc = db_session.get(ManagedDocument, uuid.UUID(created["id"]))
    assert doc is not None
    original_status = doc.status
    settings = _settings()
    first = check_service.run_check(db_session, ctx, document_id=doc.id, settings=settings)
    assert first["extraction_status"] == "extracted"
    assert first["status"] in {"completed", "needs_review"}
    assert first["legal_certification"] is False
    assert any(item["code"] == "text_extracted" for item in first["findings"])
    text = check_service.get_text(db_session, ctx, uuid.UUID(first["id"]))
    assert "T-100" in text["text"]
    db_session.refresh(doc)
    assert doc.status == original_status

    second = check_service.run_check(db_session, ctx, document_id=doc.id, settings=settings)
    assert second["idempotent"] is True
    assert second["id"] == first["id"]

    forced = check_service.run_check(db_session, ctx, document_id=doc.id, force=True, settings=settings)
    assert forced["id"] != first["id"]
    listed = check_service.list_checks(db_session, ctx, doc.id)
    assert len(listed["items"]) == 2

    worker_ctx = _ctx(HMoreRole.SUPPORT_WORKER, org.id, worker.id)
    with pytest.raises(HTTPException) as hidden:
        check_service.get_check(db_session, worker_ctx, uuid.UUID(first["id"]))
    assert hidden.value.status_code == 404
    owned = md_service.create_document_with_file(
        db_session,
        worker_ctx,
        DocumentCreate(title="Worker note", category_id=category.id, links=[]),
        filename="note.txt",
        content_type="text/plain",
        data=b"Support note recorded for the assigned case.",
    )
    worker_check = check_service.run_check(
        db_session, worker_ctx, document_id=uuid.UUID(owned["id"]), settings=settings
    )
    finding_id = uuid.UUID(worker_check["findings"][0]["id"])
    with pytest.raises(HTTPException) as denied:
        check_service.decide_finding(db_session, worker_ctx, finding_id, decision="confirm", review_comment=None)
    assert denied.value.status_code == 403

    reviewed = check_service.decide_finding(
        db_session, ctx, uuid.UUID(first["findings"][0]["id"]), decision="confirm", review_comment="Seen"
    )
    assert any(item["review_status"] == "confirmed" for item in reviewed["findings"])
    db_session.refresh(doc)
    assert doc.status == original_status

    actions = set(
        db_session.scalars(select(AuditEvent.action).where(AuditEvent.organisation_id == org.id)).all()
    )
    assert audit_events.AI_DOCUMENT_CHECK_REQUESTED in actions
    assert audit_events.AI_DOCUMENT_CHECK_RULES_COMPLETED in actions


@pytest.mark.postgres
def test_f36_ai_failures_keep_rule_results(db_session: Session, unique_suffix: str, monkeypatch: pytest.MonkeyPatch) -> None:
    apply_platform_rls_bypass(db_session)
    org, _other, admin, _worker, category = _seed(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    apply_organisation_rls(db_session, org.id)
    check_service.save_rule(
        db_session, ctx, category_code="general", rule_kind="require_phrase", parameter="MISSING-PHRASE", enabled=True
    )
    created = md_service.create_document_with_file(
        db_session,
        ctx,
        DocumentCreate(title="Letter", category_id=category.id, links=[]),
        filename="letter.pdf",
        content_type="application/pdf",
        data=build_simple_pdf("Support letter", ["This letter has no configured phrase."]),
    )
    doc_id = uuid.UUID(created["id"])
    settings = _settings(ai_service_base_url="http://ai.test", ai_service_token="token")

    def _budget(*_a, **_k):
        raise HTTPException(status_code=402, detail={"error": "ai_budget_exceeded"})

    monkeypatch.setattr(check_service, "explain_gaps", _budget)
    capped = check_service.run_check(db_session, ctx, document_id=doc_id, force=True, settings=settings)
    assert capped["ai_status"] == "skipped_budget"
    assert any(item["code"] == "require_phrase" and item["outcome"] == "fail" for item in capped["findings"])

    def _invalid(*_a, **_k):
        return {"result": {"analysis": {"observations": [{"title": "x", "body": "The document is valid.", "source_finding_code": "require_phrase"}]}}}

    monkeypatch.setattr(check_service, "explain_gaps", _invalid)
    invalid = check_service.run_check(db_session, ctx, document_id=doc_id, force=True, settings=settings)
    assert invalid["ai_status"] == "failed"
    assert invalid["observations"] == []
    assert any(item["outcome"] == "fail" for item in invalid["findings"])


@pytest.mark.postgres
def test_f36_image_and_cross_org(db_session: Session, unique_suffix: str) -> None:
    apply_platform_rls_bypass(db_session)
    org, other, admin, _worker, category = _seed(db_session, unique_suffix)
    ctx = _ctx(HMoreRole.ORGANISATION_ADMIN, org.id, admin.id)
    apply_organisation_rls(db_session, org.id)
    created = md_service.create_document_with_file(
        db_session,
        ctx,
        DocumentCreate(title="Scan", category_id=category.id, links=[]),
        filename="scan.png",
        content_type="image/png",
        data=b"\x89PNG\r\n\x1a\n" + b"not-pixels",
    )
    result = check_service.run_check(
        db_session, ctx, document_id=uuid.UUID(created["id"]), settings=_settings()
    )
    assert result["extraction_status"] == "ocr_unavailable"
    assert result["status"] == "needs_review"
    other_admin = User(email=f"oa-{unique_suffix}@example.com", display_name="OA", external_subject=f"auth0|{uuid.uuid4()}")
    db_session.add(other_admin)
    db_session.flush()
    db_session.add(
        OrganisationMembership(
            user_id=other_admin.id, organisation_id=other.id, role=HMoreRole.ORGANISATION_ADMIN, status=MembershipStatus.ACTIVE
        )
    )
    db_session.flush()
    with pytest.raises(HTTPException) as denied:
        check_service.get_check(
            db_session,
            _ctx(HMoreRole.ORGANISATION_ADMIN, other.id, other_admin.id),
            uuid.UUID(result["id"]),
        )
    assert denied.value.status_code in {403, 404}
