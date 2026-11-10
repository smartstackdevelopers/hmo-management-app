"""Tenant-scoped document submission. Does not grant documents.upload."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.core.config import Settings, get_settings
from app.db.models.managed_documents import (
    ManagedDocument,
    ManagedDocumentCategory,
    ManagedDocumentLink,
    ManagedDocumentVersion,
)
from app.managed_documents.service import _next_ref
from app.records.audit_hook import record_crud_event
from app.storage import service as storage_service
from app.storage.protocol import StorageBackend
from app.storage.validation import sniff_content_type
from app.tenant_portal.profile import require_own_tenant
from app.tenancy.context import OrganisationContext

TENANT_SUBMISSION_CODE = "tenant_submission"
TENANT_SUBMISSION_TITLE = "Tenant submissions"


def assert_tenant_submission_type(data: bytes, declared: str | None) -> None:
    """Accept PDF and image uploads only. Other types are rejected with 400."""
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    sniffed = sniff_content_type(data, declared)
    if sniffed == "application/pdf" or sniffed.startswith("image/"):
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Only PDF and image files are accepted",
    )


def get_or_create_submission_category(session: Session, organisation_id: uuid.UUID) -> ManagedDocumentCategory:
    row = session.scalar(
        select(ManagedDocumentCategory).where(
            ManagedDocumentCategory.organisation_id == organisation_id,
            ManagedDocumentCategory.code == TENANT_SUBMISSION_CODE,
        )
    )
    if row is not None:
        return row
    row = ManagedDocumentCategory(
        organisation_id=organisation_id,
        code=TENANT_SUBMISSION_CODE,
        title=TENANT_SUBMISSION_TITLE,
        access_classification="standard",
        is_active=True,
        sort_order=110,
    )
    session.add(row)
    session.flush()
    return row


def upload_own_document(
    session: Session,
    ctx: OrganisationContext,
    *,
    title: str,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    settings: Settings | None = None,
    backend: StorageBackend | None = None,
) -> dict[str, Any]:
    """Create a standard document linked only to the caller's tenant row.

    The caller cannot choose another tenant id or a category id. Both are taken
    from the signed-in tenant and the tenant_submission category.
    """
    tenant = require_own_tenant(session, ctx)
    cleaned = title.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title is required")
    if len(cleaned) > 255:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title is too long")
    assert_tenant_submission_type(data, content_type)

    category = get_or_create_submission_category(session, ctx.organisation_id)
    doc = ManagedDocument(
        organisation_id=ctx.organisation_id,
        reference_number=_next_ref(session, ctx.organisation_id),
        title=cleaned,
        category_id=category.id,
        status="draft",
        access_classification="standard",
        uploaded_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
        expiry_tracking="none",
        retention_status="none",
    )
    session.add(doc)
    session.flush()

    meta = storage_service.upload_file(
        session,
        ctx,
        filename=filename,
        declared_content_type=content_type,
        data=data,
        resource_type="managed_document_version",
        resource_id=str(doc.id),
        settings=settings,
        backend=backend,
    )
    version = ManagedDocumentVersion(
        organisation_id=ctx.organisation_id,
        document_id=doc.id,
        version_number=1,
        file_id=uuid.UUID(meta["id"]),
        change_description="Tenant submission",
        uploaded_by_user_id=ctx.user_id,
    )
    session.add(version)
    session.flush()
    doc.current_version_id = version.id
    doc.status = "active"
    session.add(
        ManagedDocumentLink(
            organisation_id=ctx.organisation_id,
            document_id=doc.id,
            link_type="tenant",
            link_id=tenant.id,
            label="Tenant submission",
        )
    )
    record_crud_event(
        session,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        action=audit_events.DOCUMENT_CREATE,
        resource_type="managed_document",
        resource_id=doc.id,
        summary=f"Tenant submitted document {doc.reference_number}",
        metadata={"category_code": TENANT_SUBMISSION_CODE},
    )
    session.flush()
    return {
        "id": doc.id,
        "title": doc.title,
        "reference_number": doc.reference_number,
        "status": doc.status,
        "access_classification": doc.access_classification,
        "category_code": TENANT_SUBMISSION_CODE,
    }
