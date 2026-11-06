"""F2.11 managed documents API (versions, expiry, retention, access, signatures)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.managed_documents import service as md_service
from app.managed_documents.schemas import (
    AccessRequestCreate,
    AccessRequestDecide,
    AccessGrantRevoke,
    CategoryCreate,
    CategoryUpdate,
    DocumentCreate,
    DocumentUpdate,
    ExpiryUpdate,
    OrgDocSettingsUpdate,
    RetentionReviewCreate,
    RetentionUpdate,
    SignatureConsent,
    SignatureDecline,
    SignatureRequestCreate,
    VersionCreateMeta,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/documents", tags=["managed-documents"])


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


# --- Dashboard & settings ---


@router.get("/dashboard", response_model=dict[str, Any])
def documents_dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.dashboard(session, org)


@router.get("/settings", response_model=dict[str, Any])
def get_document_settings(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.get_settings_view(session, org)


@router.patch("/settings", response_model=dict[str, Any])
def patch_document_settings(
    body: OrgDocSettingsUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.update_settings(session, org, body)


@router.post("/categories/seed-defaults", response_model=dict[str, Any])
def seed_default_categories(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.seed_default_categories(session, org)


# --- Categories ---


@router.post("/categories", response_model=dict[str, Any], status_code=201)
def create_category(
    body: CategoryCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.create_category(session, org, body)


@router.get("/categories", response_model=list[dict[str, Any]])
def list_categories(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return md_service.list_categories(session, org)


@router.patch("/categories/{category_id}", response_model=dict[str, Any])
def patch_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.update_category(session, org, category_id, body)


# --- Organisation-wide lists (static paths before /{doc_id}) ---


@router.post("", response_model=dict[str, Any], status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    metadata: str = Form(..., description="JSON body matching DocumentCreate"),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        body = DocumentCreate.model_validate_json(metadata)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Invalid metadata JSON: {exc}") from exc
    data = await file.read()
    return md_service.create_document_with_file(
        session,
        org,
        body,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
    )


@router.get("", response_model=dict[str, Any])
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=255),
    category_id: uuid.UUID | None = None,
    status_filter: str | None = Query(None, alias="status", max_length=32),
    link_type: str | None = Query(None, max_length=32),
    link_id: uuid.UUID | None = None,
    expiry_status: str | None = Query(None, max_length=32),
    retention_status: str | None = Query(None, max_length=32),
    signature_status: str | None = Query(None, max_length=32),
    uploader_user_id: uuid.UUID | None = None,
    sort: str = Query("-created_at", max_length=32),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items, total = md_service.list_documents(
        session,
        org,
        page=page,
        page_size=page_size,
        q=q,
        category_id=category_id,
        status=status_filter,
        link_type=link_type,
        link_id=link_id,
        expiry_status=expiry_status,
        retention_status=retention_status,
        signature_status=signature_status,
        uploader_user_id=uploader_user_id,
        sort=sort,
    )
    return _page(items, page, page_size, total)


@router.get("/recent", response_model=dict[str, Any])
def list_recent_documents(
    limit: int = Query(10, ge=1, le=50),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return {"items": md_service.list_recent_documents(session, org, limit=limit)}


@router.get("/expiring", response_model=dict[str, Any])
def list_expiring_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items, total = md_service.list_documents(
        session,
        org,
        page=page,
        page_size=page_size,
        expiry_status="expiring_soon",
        sort="expiry_date",
    )
    return _page(items, page, page_size, total)


@router.get("/expired", response_model=dict[str, Any])
def list_expired_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items, total = md_service.list_documents(
        session,
        org,
        page=page,
        page_size=page_size,
        expiry_status="expired",
        sort="-expiry_date",
    )
    return _page(items, page, page_size, total)


@router.get("/retention/pending-review", response_model=dict[str, Any])
def list_retention_pending_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items, total = md_service.list_documents(
        session,
        org,
        page=page,
        page_size=page_size,
        retention_status="pending_review",
        sort="-updated_at",
    )
    return _page(items, page, page_size, total)


@router.get("/me/access-requests", response_model=list[dict[str, Any]])
def list_my_access_requests(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return md_service.list_my_access_requests(session, org)


@router.get("/access-requests/pending-review", response_model=list[dict[str, Any]])
def list_pending_access_requests(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return md_service.list_pending_access_requests(session, org)


@router.post("/access-requests/{request_id}/decide", response_model=dict[str, Any])
def decide_access_request(
    request_id: uuid.UUID,
    body: AccessRequestDecide,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.decide_access_request(session, org, request_id, body)


@router.post("/access-grants/{grant_id}/revoke", response_model=dict[str, Any])
def revoke_access_grant(
    grant_id: uuid.UUID,
    body: AccessGrantRevoke | None = Body(default=None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.revoke_access_grant(session, org, grant_id, body)


@router.get("/signature-requests/pending", response_model=list[dict[str, Any]])
def list_all_pending_signatures(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return md_service.list_pending_signatures_for_org(session, org)


@router.get("/me/signature-requests", response_model=list[dict[str, Any]])
def list_my_pending_signatures(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return md_service.list_my_pending_signatures(session, org)


@router.get("/signature-requests/{sig_id}", response_model=dict[str, Any])
def get_signature_request(
    sig_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.get_signature_request(session, org, sig_id)


@router.post("/signature-requests/{sig_id}/complete", response_model=dict[str, Any])
def complete_signature(
    sig_id: uuid.UUID,
    body: SignatureConsent,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.complete_signature(session, org, sig_id, body)


@router.post("/signature-requests/{sig_id}/decline", response_model=dict[str, Any])
def decline_signature(
    sig_id: uuid.UUID,
    body: SignatureDecline,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.decline_signature(session, org, sig_id, body)


# --- Per-document routes ---


@router.get("/{doc_id}", response_model=dict[str, Any])
def get_document(
    doc_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.get_document(session, org, doc_id)


@router.patch("/{doc_id}", response_model=dict[str, Any])
def patch_document(
    doc_id: uuid.UUID,
    body: DocumentUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.update_document(session, org, doc_id, body)


@router.post("/{doc_id}/archive", response_model=dict[str, Any])
def archive_document(
    doc_id: uuid.UUID,
    reason: str | None = Query(None, max_length=4000),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.archive_document(session, org, doc_id, reason)


@router.get("/{doc_id}/content", response_class=Response)
def download_current_version(
    doc_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    from urllib.parse import quote

    d = md_service.get_document(session, org, doc_id)
    cv = d.get("current_version_id")
    if not cv:
        raise HTTPException(status_code=404, detail="No current version")
    row, data, filename = md_service.download_version(session, org, doc_id, uuid.UUID(cv))
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=data,
        media_type=row.content_type,
        headers={
            "Content-Disposition": disposition,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


# --- Versions ---


@router.get("/{doc_id}/versions", response_model=list[dict[str, Any]])
def list_document_versions(
    doc_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return md_service.list_versions(session, org, doc_id)


@router.post("/{doc_id}/versions", response_model=dict[str, Any], status_code=201)
async def upload_document_version(
    doc_id: uuid.UUID,
    file: UploadFile = File(...),
    metadata: str = Form(default="{}", description="JSON: VersionCreateMeta"),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        meta = VersionCreateMeta.model_validate_json(metadata) if metadata.strip() else VersionCreateMeta()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid metadata JSON: {exc}") from exc
    data = await file.read()
    return md_service.add_version(
        session,
        org,
        doc_id,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
        meta=meta,
    )


@router.get("/{doc_id}/versions/{version_id}/content", response_class=Response)
def download_document_version(
    doc_id: uuid.UUID,
    version_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    from urllib.parse import quote

    row, data, filename = md_service.download_version(session, org, doc_id, version_id)
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=data,
        media_type=row.content_type,
        headers={
            "Content-Disposition": disposition,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


# --- Expiry & retention ---


@router.patch("/{doc_id}/expiry", response_model=dict[str, Any])
def patch_document_expiry(
    doc_id: uuid.UUID,
    body: ExpiryUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.update_expiry(session, org, doc_id, body)


@router.get("/{doc_id}/expiry-status", response_model=dict[str, Any])
def get_document_expiry_status(
    doc_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    d = md_service.get_document(session, org, doc_id)
    return {
        "document_id": d["id"],
        "expiry_date": d.get("expiry_date"),
        "expiry_tracking": d.get("expiry_tracking"),
    }


@router.patch("/{doc_id}/retention", response_model=dict[str, Any])
def patch_document_retention(
    doc_id: uuid.UUID,
    body: RetentionUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.update_retention(session, org, doc_id, body)


@router.post("/{doc_id}/retention/reviews", response_model=dict[str, Any], status_code=201)
def post_retention_review(
    doc_id: uuid.UUID,
    body: RetentionReviewCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.add_retention_review(session, org, doc_id, body)


# --- Access requests (per document) ---


@router.post("/{doc_id}/access-requests", response_model=dict[str, Any], status_code=201)
def create_access_request(
    doc_id: uuid.UUID,
    body: AccessRequestCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.create_access_request(session, org, doc_id, body)


# --- Signatures (per document) ---


@router.post("/{doc_id}/signature-requests", response_model=dict[str, Any], status_code=201)
def create_signature_request(
    doc_id: uuid.UUID,
    body: SignatureRequestCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return md_service.create_signature_request(session, org, doc_id, body)


@router.get("/{doc_id}/signature-requests", response_model=list[dict[str, Any]])
def list_signature_requests_for_doc(
    doc_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return md_service.list_signature_requests(session, org, doc_id)
