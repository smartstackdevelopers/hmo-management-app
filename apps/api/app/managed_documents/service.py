"""F2.11 managed documents service."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import get_settings
from app.db.models.file_metadata import FileMetadata
from app.db.models.managed_documents import (
    ManagedDocument,
    ManagedDocumentAccessGrant,
    ManagedDocumentAccessRequest,
    ManagedDocumentCategory,
    ManagedDocumentLink,
    ManagedDocumentReminderLog,
    ManagedDocumentRetentionReview,
    ManagedDocumentSignatureRequest,
    ManagedDocumentVersion,
    OrganisationDocumentSettings,
)
from app.managed_documents import access as md_access
from app.managed_documents.schemas import (
    AccessGrantRevoke,
    AccessRequestCreate,
    AccessRequestDecide,
    CategoryCreate,
    CategoryUpdate,
    DocumentCreate,
    DocumentLinkIn,
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
from app.records.pagination import offset_limit
from app.storage import service as storage_service
from app.tenancy.context import OrganisationContext

NOW = lambda: datetime.now(timezone.utc)

_MIN_UTC = datetime.min.replace(tzinfo=timezone.utc)


def _next_ref(session: Session, org_id: uuid.UUID) -> str:
    year = NOW().year
    pat = f"MD-{year}-"
    from app.db.models.managed_documents import ManagedDocument as MD

    count = (
        session.scalar(
            select(func.count()).select_from(MD).where(
                MD.organisation_id == org_id,
                MD.reference_number.like(f"{pat}%"),
            )
        )
        or 0
    )
    return f"{pat}{count + 1:05d}"


def _audit(
    session: Session,
    ctx: OrganisationContext,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    record_event(
        session,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS.value,
        summary=summary,
        metadata=metadata or {},
    )


def compute_expiry_tracking(d: ManagedDocument, settings: OrganisationDocumentSettings | None) -> str:
    if d.expiry_date is None:
        return "none"
    today = date.today()
    ed = d.expiry_date
    if ed < today:
        return "expired"
    days_first = (settings.expiry_reminder_days_first if settings else 30)
    if (ed - today).days <= days_first:
        return "expiring_soon"
    return "valid"


def _sync_expiry_fields(session: Session, d: ManagedDocument) -> None:
    """Align stored expiry_tracking with computed value from expiry_date and org settings."""
    s = md_access.get_or_create_settings(session, d.organisation_id)
    d.expiry_tracking = compute_expiry_tracking(d, s)


DEFAULT_CATEGORY_SEED: list[tuple[str, str, str, int]] = [
    ("tenant_documents", "Tenant documents", "standard", 10),
    ("identity_documents", "Identity documents", "confidential", 20),
    ("housing_application_documents", "Housing application documents", "standard", 30),
    ("support_plan_documents", "Support plan documents", "standard", 40),
    ("property_documents", "Property documents", "standard", 50),
    ("maintenance_documents", "Maintenance documents", "standard", 60),
    ("complaints_related", "Complaints-related documents", "standard", 70),
    ("agreements_contracts", "Agreements and contracts", "restricted", 80),
    ("training_safeguarding", "Training and safeguarding documents", "restricted", 90),
    ("other", "Other", "standard", 1000),
]


def seed_default_categories(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    """Create suggested categories when missing (idempotent per org/code)."""
    md_access.require_categories(ctx)
    created = 0
    for code, title, cls, sort in DEFAULT_CATEGORY_SEED:
        existing = session.scalar(
            select(ManagedDocumentCategory.id).where(
                ManagedDocumentCategory.organisation_id == ctx.organisation_id,
                ManagedDocumentCategory.code == code,
            )
        )
        if existing:
            continue
        session.add(
            ManagedDocumentCategory(
                organisation_id=ctx.organisation_id,
                code=code,
                title=title,
                access_classification=cls,
                sort_order=sort,
            )
        )
        created += 1
    session.flush()
    return {"created": created, "categories": list_categories(session, ctx)}


def _doc_dict(session: Session, d: ManagedDocument) -> dict[str, Any]:
    cat = session.get(ManagedDocumentCategory, d.category_id)
    settings = md_access.get_or_create_settings(session, d.organisation_id)
    eff = md_access.effective_classification(d, cat)
    links = list(
        session.scalars(select(ManagedDocumentLink).where(ManagedDocumentLink.document_id == d.id))
    )
    return {
        "id": str(d.id),
        "reference_number": d.reference_number,
        "title": d.title,
        "description": d.description,
        "category_id": str(d.category_id),
        "category_code": cat.code if cat else None,
        "status": d.status,
        "access_classification": d.access_classification,
        "effective_classification": eff,
        "uploaded_by_user_id": str(d.uploaded_by_user_id) if d.uploaded_by_user_id else None,
        "current_version_id": str(d.current_version_id) if d.current_version_id else None,
        "expiry_date": d.expiry_date.isoformat() if d.expiry_date else None,
        "expiry_tracking": compute_expiry_tracking(d, settings),
        "expiry_updated_reason": d.expiry_updated_reason,
        "retention_policy_label": d.retention_policy_label,
        "retention_start_date": d.retention_start_date.isoformat() if d.retention_start_date else None,
        "retention_review_due_at": d.retention_review_due_at.isoformat() if d.retention_review_due_at else None,
        "retention_status": d.retention_status,
        "legal_hold": d.legal_hold,
        "archived_at": d.archived_at.isoformat() if d.archived_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        "links": [
            {"id": str(l.id), "link_type": l.link_type, "link_id": str(l.link_id), "label": l.label}
            for l in links
        ],
    }


def _apply_links(
    session: Session,
    ctx: OrganisationContext,
    doc: ManagedDocument,
    links: list[DocumentLinkIn],
) -> None:
    session.execute(delete(ManagedDocumentLink).where(ManagedDocumentLink.document_id == doc.id))
    for li in links:
        row = ManagedDocumentLink(
            organisation_id=ctx.organisation_id,
            document_id=doc.id,
            link_type=li.link_type,
            link_id=li.link_id,
            label=li.label,
        )
        md_access.validate_link_for_write(session, ctx, row)
        session.add(row)


# --- Categories ---


def create_category(
    session: Session, ctx: OrganisationContext, body: CategoryCreate
) -> dict[str, Any]:
    md_access.require_categories(ctx)
    row = ManagedDocumentCategory(
        organisation_id=ctx.organisation_id,
        code=body.code.strip().lower().replace(" ", "_")[:64],
        title=body.title.strip(),
        description=body.description,
        access_classification=body.access_classification,
        sort_order=body.sort_order,
    )
    session.add(row)
    session.flush()
    _audit(session, ctx, audit_events.DOCUMENT_CATEGORY_CREATE, "document_category", row.id, f"Category {row.code}")
    return {
        "id": str(row.id),
        "code": row.code,
        "title": row.title,
        "access_classification": row.access_classification,
        "is_active": row.is_active,
    }


def list_categories(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    md_access.require_meta(ctx)
    rows = list(
        session.scalars(
            select(ManagedDocumentCategory)
            .where(ManagedDocumentCategory.organisation_id == ctx.organisation_id)
            .order_by(ManagedDocumentCategory.sort_order, ManagedDocumentCategory.title)
        )
    )
    return [
        {
            "id": str(r.id),
            "code": r.code,
            "title": r.title,
            "access_classification": r.access_classification,
            "is_active": r.is_active,
        }
        for r in rows
    ]


def update_category(
    session: Session, ctx: OrganisationContext, category_id: uuid.UUID, body: CategoryUpdate
) -> dict[str, Any]:
    md_access.require_categories(ctx)
    row = session.get(ManagedDocumentCategory, category_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Category not found")
    if body.title is not None:
        row.title = body.title
    if body.description is not None:
        row.description = body.description
    if body.access_classification is not None:
        row.access_classification = body.access_classification
    if body.is_active is not None:
        row.is_active = body.is_active
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    _audit(session, ctx, audit_events.DOCUMENT_CATEGORY_UPDATE, "document_category", row.id, "Category updated")
    session.flush()
    return {"id": str(row.id), "code": row.code, "title": row.title}


def get_settings_view(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    md_access.require_meta(ctx)
    s = md_access.get_or_create_settings(session, ctx.organisation_id)
    return {
        "expiry_reminder_days_first": s.expiry_reminder_days_first,
        "expiry_reminder_days_urgent": s.expiry_reminder_days_urgent,
        "expiry_reminder_repeat_hours": s.expiry_reminder_repeat_hours,
        "retention_default_review_months": s.retention_default_review_months,
    }


def update_settings(session: Session, ctx: OrganisationContext, body: OrgDocSettingsUpdate) -> dict[str, Any]:
    md_access.require_settings(ctx)
    s = md_access.get_or_create_settings(session, ctx.organisation_id)
    if body.expiry_reminder_days_first is not None:
        s.expiry_reminder_days_first = body.expiry_reminder_days_first
    if body.expiry_reminder_days_urgent is not None:
        s.expiry_reminder_days_urgent = body.expiry_reminder_days_urgent
    if body.expiry_reminder_repeat_hours is not None:
        s.expiry_reminder_repeat_hours = body.expiry_reminder_repeat_hours
    if body.retention_default_review_months is not None:
        s.retention_default_review_months = body.retention_default_review_months
    _audit(session, ctx, audit_events.DOCUMENT_SETTINGS_UPDATE, "document_settings", s.id, "Document settings updated")
    session.flush()
    return get_settings_view(session, ctx)


def create_document_with_file(
    session: Session,
    ctx: OrganisationContext,
    body: DocumentCreate,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
) -> dict[str, Any]:
    md_access.require_upload(ctx)
    cat = session.get(ManagedDocumentCategory, body.category_id)
    if cat is None or cat.organisation_id != ctx.organisation_id or not cat.is_active:
        raise HTTPException(status_code=400, detail="Invalid category")

    if body.access_classification in {"confidential", "restricted"}:
        md_access.require_restricted_view(ctx)

    ref = _next_ref(session, ctx.organisation_id)
    doc = ManagedDocument(
        organisation_id=ctx.organisation_id,
        reference_number=ref,
        title=body.title.strip(),
        description=body.description,
        category_id=body.category_id,
        status="draft",
        access_classification=body.access_classification,
        uploaded_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
        expiry_date=body.expiry_date,
        retention_policy_label=body.retention_policy_label,
        retention_start_date=body.retention_start_date,
        retention_review_due_at=body.retention_review_due_at,
        legal_hold=body.legal_hold,
    )
    session.add(doc)
    session.flush()
    _sync_expiry_fields(session, doc)

    meta = storage_service.upload_file(
        session,
        ctx,
        filename=filename,
        declared_content_type=content_type,
        data=data,
        resource_type="managed_document_version",
        resource_id=str(doc.id),
    )
    file_id = uuid.UUID(meta["id"])

    ver = ManagedDocumentVersion(
        organisation_id=ctx.organisation_id,
        document_id=doc.id,
        version_number=1,
        file_id=file_id,
        change_description="Initial upload",
        uploaded_by_user_id=ctx.user_id,
    )
    session.add(ver)
    session.flush()
    doc.current_version_id = ver.id
    doc.status = "active"

    for li in body.links:
        row = ManagedDocumentLink(
            organisation_id=ctx.organisation_id,
            document_id=doc.id,
            link_type=li.link_type,
            link_id=li.link_id,
            label=li.label,
        )
        md_access.validate_link_for_write(session, ctx, row)
        session.add(row)

    _audit(
        session,
        ctx,
        audit_events.DOCUMENT_CREATE,
        "managed_document",
        doc.id,
        f"Created document {ref}",
        metadata={"version_id": str(ver.id)},
    )
    session.flush()
    return _doc_dict(session, doc)


def list_documents(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    q: str | None,
    category_id: uuid.UUID | None,
    status: str | None,
    link_type: str | None,
    link_id: uuid.UUID | None,
    expiry_status: str | None,
    retention_status: str | None,
    signature_status: str | None,
    uploader_user_id: uuid.UUID | None,
    sort: str,
) -> tuple[list[dict[str, Any]], int]:
    md_access.require_meta(ctx)
    stmt = select(ManagedDocument).where(ManagedDocument.organisation_id == ctx.organisation_id)
    if q:
        stmt = stmt.where(
            or_(
                ManagedDocument.title.ilike(f"%{q}%"),
                ManagedDocument.reference_number.ilike(f"%{q}%"),
            )
        )
    if category_id:
        stmt = stmt.where(ManagedDocument.category_id == category_id)
    if status:
        stmt = stmt.where(ManagedDocument.status == status)
    if uploader_user_id:
        stmt = stmt.where(ManagedDocument.uploaded_by_user_id == uploader_user_id)
    if retention_status:
        stmt = stmt.where(ManagedDocument.retention_status == retention_status)
    if link_type and link_id:
        stmt = stmt.where(
            ManagedDocument.id.in_(
                select(ManagedDocumentLink.document_id).where(
                    ManagedDocumentLink.link_type == link_type,
                    ManagedDocumentLink.link_id == link_id,
                )
            )
        )

    rows = list(session.scalars(stmt))
    settings = md_access.get_or_create_settings(session, ctx.organisation_id)
    out: list[dict[str, Any]] = []
    for d in rows:
        if not md_access.document_visible(session, ctx, d):
            continue
        ddict = _doc_dict(session, d)
        et = ddict["expiry_tracking"]
        if expiry_status:
            if expiry_status == "no_expiry" and d.expiry_date is not None:
                continue
            if expiry_status != "no_expiry" and et != expiry_status:
                continue
        if signature_status:
            sig = session.scalar(
                select(ManagedDocumentSignatureRequest.status)
                .where(ManagedDocumentSignatureRequest.document_id == d.id)
                .order_by(ManagedDocumentSignatureRequest.created_at.desc())
                .limit(1)
            )
            if sig != signature_status:
                continue
        out.append(ddict)

    reverse = sort.startswith("-")
    key = sort.lstrip("-")
    if key == "expiry_date":

        def sk(x: dict[str, Any]) -> date | None:
            raw = x.get("expiry_date")
            if not raw:
                return None
            return date.fromisoformat(raw)

        out.sort(key=sk, reverse=reverse)
    elif key == "title":
        out.sort(key=lambda x: x["title"].lower(), reverse=reverse)
    elif key == "updated_at":
        out.sort(key=lambda x: x.get("updated_at") or "", reverse=reverse)
    else:
        out.sort(key=lambda x: x.get("created_at") or "", reverse=reverse)

    total = len(out)
    offset, limit = offset_limit(page, page_size)
    return out[offset : offset + limit], total


def list_recent_documents(session: Session, ctx: OrganisationContext, *, limit: int) -> list[dict[str, Any]]:
    md_access.require_meta(ctx)
    rows = list(
        session.scalars(
            select(ManagedDocument)
            .where(ManagedDocument.organisation_id == ctx.organisation_id)
            .order_by(ManagedDocument.updated_at.desc())
            .limit(limit * 5)
        )
    )
    out: list[dict[str, Any]] = []
    for d in rows:
        if not md_access.document_visible(session, ctx, d):
            continue
        out.append(_doc_dict(session, d))
        if len(out) >= limit:
            break
    return out


def get_document(session: Session, ctx: OrganisationContext, doc_id: uuid.UUID) -> dict[str, Any]:
    d = md_access.assert_document_readable(session, ctx, doc_id)
    return _doc_dict(session, d)


def update_document(
    session: Session, ctx: OrganisationContext, doc_id: uuid.UUID, body: DocumentUpdate
) -> dict[str, Any]:
    d = md_access.assert_document_readable(session, ctx, doc_id)
    if d.status == "archived":
        raise HTTPException(status_code=409, detail="Archived document")
    md_access.require_upload(ctx)
    if body.title is not None:
        d.title = body.title
    if body.description is not None:
        d.description = body.description
    if body.category_id is not None:
        cat = session.get(ManagedDocumentCategory, body.category_id)
        if cat is None or cat.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=400, detail="Invalid category")
        d.category_id = body.category_id
    if body.access_classification is not None:
        if body.access_classification in {"confidential", "restricted"}:
            md_access.require_restricted_view(ctx)
        d.access_classification = body.access_classification
    if body.links is not None:
        _apply_links(session, ctx, d, body.links)
    d.updated_by_user_id = ctx.user_id
    _audit(session, ctx, audit_events.DOCUMENT_UPDATE, "managed_document", d.id, "Metadata updated")
    session.flush()
    return _doc_dict(session, d)


def add_version(
    session: Session,
    ctx: OrganisationContext,
    doc_id: uuid.UUID,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    meta: VersionCreateMeta,
) -> dict[str, Any]:
    d = md_access.assert_document_readable(session, ctx, doc_id)
    md_access.require_version(ctx)
    if d.status != "active":
        raise HTTPException(status_code=409, detail="Document not active")

    pending = session.scalar(
        select(ManagedDocumentSignatureRequest.id).where(
            ManagedDocumentSignatureRequest.document_id == doc_id,
            ManagedDocumentSignatureRequest.status.in_(["pending_signature", "draft"]),
        )
    )
    if pending:
        raise HTTPException(status_code=409, detail="Resolve open signature requests first")

    max_ver = (
        session.scalar(select(func.max(ManagedDocumentVersion.version_number)).where(ManagedDocumentVersion.document_id == doc_id))
        or 0
    )
    storage_meta = storage_service.upload_file(
        session,
        ctx,
        filename=filename,
        declared_content_type=content_type,
        data=data,
        resource_type="managed_document_version",
        resource_id=str(doc_id),
    )
    file_id = uuid.UUID(storage_meta["id"])
    ver = ManagedDocumentVersion(
        organisation_id=ctx.organisation_id,
        document_id=doc_id,
        version_number=max_ver + 1,
        file_id=file_id,
        change_description=meta.change_description,
        uploaded_by_user_id=ctx.user_id,
    )
    session.add(ver)
    session.flush()
    d.current_version_id = ver.id
    d.updated_by_user_id = ctx.user_id
    _sync_expiry_fields(session, d)
    _audit(
        session,
        ctx,
        audit_events.DOCUMENT_VERSION_CREATE,
        "managed_document_version",
        ver.id,
        f"Version {ver.version_number}",
        metadata={"document_id": str(doc_id)},
    )
    session.flush()
    return {
        "version_id": str(ver.id),
        "version_number": ver.version_number,
        "file": storage_meta,
    }


def list_versions(session: Session, ctx: OrganisationContext, doc_id: uuid.UUID) -> list[dict[str, Any]]:
    md_access.assert_document_readable(session, ctx, doc_id)
    rows = list(
        session.scalars(
            select(ManagedDocumentVersion)
            .where(ManagedDocumentVersion.document_id == doc_id)
            .order_by(ManagedDocumentVersion.version_number.desc())
        )
    )
    return [
        {
            "id": str(v.id),
            "version_number": v.version_number,
            "change_description": v.change_description,
            "file_id": str(v.file_id),
            "uploaded_by_user_id": str(v.uploaded_by_user_id) if v.uploaded_by_user_id else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in rows
    ]


def download_version(
    session: Session, ctx: OrganisationContext, doc_id: uuid.UUID, version_id: uuid.UUID
) -> tuple[Any, bytes, str]:
    md_access.assert_document_readable(session, ctx, doc_id)
    md_access.require_content(ctx)
    v = session.get(ManagedDocumentVersion, version_id)
    if v is None or v.document_id != doc_id or v.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Version not found")
    row, data = storage_service.download_file(session, ctx, v.file_id)
    _audit(
        session,
        ctx,
        audit_events.DOCUMENT_VERSION_DOWNLOAD,
        "managed_document_version",
        v.id,
        "Version downloaded",
        metadata={"file_id": str(v.file_id)},
    )
    session.flush()
    return row, data, row.original_filename


def archive_document(session: Session, ctx: OrganisationContext, doc_id: uuid.UUID, reason: str | None) -> dict[str, Any]:
    d = md_access.assert_document_readable(session, ctx, doc_id)
    md_access.require_archive(ctx)
    d.status = "archived"
    d.archived_at = NOW()
    d.archived_by_user_id = ctx.user_id
    d.archive_reason = reason
    _audit(session, ctx, audit_events.DOCUMENT_ARCHIVE, "managed_document", d.id, "Document archived")
    session.flush()
    return _doc_dict(session, d)


def update_expiry(session: Session, ctx: OrganisationContext, doc_id: uuid.UUID, body: ExpiryUpdate) -> dict[str, Any]:
    d = md_access.assert_document_readable(session, ctx, doc_id)
    md_access.require_expiry_manage(ctx)
    if body.expiry_date is not None:
        d.expiry_date = body.expiry_date
    if body.reason:
        d.expiry_updated_reason = body.reason
    if body.expiry_tracking is not None:
        d.expiry_tracking = body.expiry_tracking
    else:
        _sync_expiry_fields(session, d)
    d.updated_by_user_id = ctx.user_id
    _audit(session, ctx, audit_events.DOCUMENT_EXPIRY_UPDATE, "managed_document", d.id, "Expiry updated")
    session.flush()
    return _doc_dict(session, d)


def update_retention(session: Session, ctx: OrganisationContext, doc_id: uuid.UUID, body: RetentionUpdate) -> dict[str, Any]:
    d = md_access.assert_document_readable(session, ctx, doc_id)
    md_access.require_retention_manage(ctx)
    if body.retention_policy_label is not None:
        d.retention_policy_label = body.retention_policy_label
    if body.retention_start_date is not None:
        d.retention_start_date = body.retention_start_date
    if body.retention_review_due_at is not None:
        d.retention_review_due_at = body.retention_review_due_at
    if body.retention_status is not None:
        d.retention_status = body.retention_status
    if body.legal_hold is not None:
        d.legal_hold = body.legal_hold
    d.updated_by_user_id = ctx.user_id
    _audit(session, ctx, audit_events.DOCUMENT_RETENTION_UPDATE, "managed_document", d.id, "Retention updated")
    session.flush()
    return _doc_dict(session, d)


def add_retention_review(
    session: Session, ctx: OrganisationContext, doc_id: uuid.UUID, body: RetentionReviewCreate
) -> dict[str, Any]:
    d = md_access.assert_document_readable(session, ctx, doc_id)
    md_access.require_retention_manage(ctx)
    row = ManagedDocumentRetentionReview(
        organisation_id=ctx.organisation_id,
        document_id=doc_id,
        reviewer_user_id=ctx.user_id,
        notes=body.notes,
        next_review_due_at=body.next_review_due_at,
    )
    session.add(row)
    if body.next_review_due_at:
        d.retention_review_due_at = body.next_review_due_at
    d.retention_status = "active"
    _audit(session, ctx, audit_events.DOCUMENT_RETENTION_REVIEW, "managed_document", d.id, "Retention review recorded")
    session.flush()
    return {"id": str(row.id), "next_review_due_at": body.next_review_due_at.isoformat() if body.next_review_due_at else None}


# --- Access requests ---


def create_access_request(
    session: Session, ctx: OrganisationContext, doc_id: uuid.UUID, body: AccessRequestCreate
) -> dict[str, Any]:
    md_access.require_access_request(ctx)
    d = session.get(ManagedDocument, doc_id)
    if d is None or d.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if not md_access.document_visible(session, ctx, d):
        raise HTTPException(status_code=404, detail="Document not found")
    row = ManagedDocumentAccessRequest(
        organisation_id=ctx.organisation_id,
        document_id=doc_id,
        requester_user_id=ctx.user_id,
        reason=body.reason,
        status="submitted",
    )
    session.add(row)
    session.flush()
    _audit(session, ctx, audit_events.DOCUMENT_ACCESS_REQUEST, "managed_document_access_request", row.id, "Access requested")
    return {"id": str(row.id), "status": row.status}


def list_my_access_requests(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    md_access.require_access_request(ctx)
    rows = list(
        session.scalars(
            select(ManagedDocumentAccessRequest)
            .where(
                ManagedDocumentAccessRequest.organisation_id == ctx.organisation_id,
                ManagedDocumentAccessRequest.requester_user_id == ctx.user_id,
            )
            .order_by(ManagedDocumentAccessRequest.created_at.desc())
        )
    )
    return [{"id": str(r.id), "document_id": str(r.document_id), "status": r.status} for r in rows]


def list_pending_access_requests(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    md_access.require_access_approve(ctx)
    rows = list(
        session.scalars(
            select(ManagedDocumentAccessRequest)
            .where(
                ManagedDocumentAccessRequest.organisation_id == ctx.organisation_id,
                ManagedDocumentAccessRequest.status.in_(["submitted", "under_review"]),
            )
            .order_by(ManagedDocumentAccessRequest.created_at.asc())
        )
    )
    return [
        {
            "id": str(r.id),
            "document_id": str(r.document_id),
            "requester_user_id": str(r.requester_user_id),
            "reason": r.reason,
            "status": r.status,
        }
        for r in rows
    ]


def decide_access_request(
    session: Session, ctx: OrganisationContext, req_id: uuid.UUID, body: AccessRequestDecide
) -> dict[str, Any]:
    md_access.require_access_approve(ctx)
    r = session.get(ManagedDocumentAccessRequest, req_id)
    if r is None or r.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Request not found")
    if r.requester_user_id == ctx.user_id:
        raise HTTPException(status_code=403, detail="Cannot approve own request")
    if r.status not in {"submitted", "under_review"}:
        raise HTTPException(status_code=409, detail="Request not actionable")
    r.decided_by_user_id = ctx.user_id
    r.decided_at = NOW()
    r.decision_reason = body.decision_reason
    if body.approve:
        r.status = "approved"
        hours = body.temporary_hours or 72
        exp = NOW() + timedelta(hours=hours)
        r.temporary_access_expires_at = exp
        grant = ManagedDocumentAccessGrant(
            organisation_id=ctx.organisation_id,
            document_id=r.document_id,
            user_id=r.requester_user_id,
            request_id=r.id,
            expires_at=exp,
        )
        session.add(grant)
        _audit(
            session,
            ctx,
            audit_events.DOCUMENT_ACCESS_GRANT,
            "managed_document_access_grant",
            grant.id,
            "Temporary access granted",
            metadata={"request_id": str(r.id)},
        )
    else:
        r.status = "rejected"
    _audit(session, ctx, audit_events.DOCUMENT_ACCESS_DECIDE, "managed_document_access_request", r.id, f"Decision: {r.status}")
    session.flush()
    return {"id": str(r.id), "status": r.status}


def revoke_access_grant(
    session: Session, ctx: OrganisationContext, grant_id: uuid.UUID, body: AccessGrantRevoke | None
) -> dict[str, Any]:
    md_access.require_access_approve(ctx)
    g = session.get(ManagedDocumentAccessGrant, grant_id)
    if g is None or g.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Grant not found")
    if g.revoked_at is not None:
        raise HTTPException(status_code=409, detail="Already revoked")
    g.revoked_at = NOW()
    _audit(
        session,
        ctx,
        audit_events.DOCUMENT_ACCESS_REVOKE,
        "managed_document_access_grant",
        g.id,
        "Temporary access revoked",
        metadata={"document_id": str(g.document_id), "reason": body.reason if body else None},
    )
    session.flush()
    return {"id": str(g.id), "revoked": True}


# --- Signatures ---


def create_signature_request(
    session: Session, ctx: OrganisationContext, doc_id: uuid.UUID, body: SignatureRequestCreate
) -> dict[str, Any]:
    md_access.assert_document_readable(session, ctx, doc_id)
    md_access.require_sign_request(ctx)
    v = session.get(ManagedDocumentVersion, body.version_id)
    if v is None or v.document_id != doc_id:
        raise HTTPException(status_code=404, detail="Version not found")
    row = ManagedDocumentSignatureRequest(
        organisation_id=ctx.organisation_id,
        document_id=doc_id,
        version_id=body.version_id,
        signer_user_id=body.signer_user_id,
        status="pending_signature",
        consent_text=body.consent_text,
        requested_by_user_id=ctx.user_id,
        requested_at=NOW(),
        expires_at=body.expires_at,
    )
    session.add(row)
    session.flush()
    _audit(session, ctx, audit_events.DOCUMENT_SIGN_REQUEST, "managed_document_signature", row.id, "Signature requested")
    return {"id": str(row.id), "status": row.status}


def list_signature_requests(session: Session, ctx: OrganisationContext, doc_id: uuid.UUID) -> list[dict[str, Any]]:
    md_access.assert_document_readable(session, ctx, doc_id)
    rows = list(
        session.scalars(
            select(ManagedDocumentSignatureRequest)
            .where(ManagedDocumentSignatureRequest.document_id == doc_id)
            .order_by(ManagedDocumentSignatureRequest.created_at.desc())
        )
    )
    return [
        {
            "id": str(r.id),
            "version_id": str(r.version_id),
            "signer_user_id": str(r.signer_user_id),
            "status": r.status,
            "signed_at": r.signed_at.isoformat() if r.signed_at else None,
        }
        for r in rows
    ]


def _signature_dict(r: ManagedDocumentSignatureRequest) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "document_id": str(r.document_id),
        "version_id": str(r.version_id),
        "signer_user_id": str(r.signer_user_id),
        "status": r.status,
        "consent_text": r.consent_text,
        "requested_at": r.requested_at.isoformat() if r.requested_at else None,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        "signed_at": r.signed_at.isoformat() if r.signed_at else None,
        "declined_at": r.declined_at.isoformat() if r.declined_at else None,
        "decline_reason": r.decline_reason,
        "signature_evidence": r.signature_evidence,
    }


def get_signature_request(session: Session, ctx: OrganisationContext, sig_id: uuid.UUID) -> dict[str, Any]:
    md_access.require_meta(ctx)
    r = session.get(ManagedDocumentSignatureRequest, sig_id)
    if r is None or r.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Signature request not found")
    md_access.assert_document_readable(session, ctx, r.document_id)
    return _signature_dict(r)


def list_pending_signatures_for_org(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    md_access.require_meta(ctx)
    rows = list(
        session.scalars(
            select(ManagedDocumentSignatureRequest)
            .where(
                ManagedDocumentSignatureRequest.organisation_id == ctx.organisation_id,
                ManagedDocumentSignatureRequest.status == "pending_signature",
            )
            .order_by(ManagedDocumentSignatureRequest.created_at.asc())
        )
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        d = session.get(ManagedDocument, r.document_id)
        if d is None:
            continue
        if not md_access.document_visible(session, ctx, d):
            continue
        out.append(_signature_dict(r))
    return out


def list_my_pending_signatures(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    md_access.require_sign_complete(ctx)
    rows = list(
        session.scalars(
            select(ManagedDocumentSignatureRequest)
            .where(
                ManagedDocumentSignatureRequest.organisation_id == ctx.organisation_id,
                ManagedDocumentSignatureRequest.signer_user_id == ctx.user_id,
                ManagedDocumentSignatureRequest.status == "pending_signature",
            )
            .order_by(ManagedDocumentSignatureRequest.created_at.asc())
        )
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        d = session.get(ManagedDocument, r.document_id)
        if d is None:
            continue
        if not md_access.document_visible(session, ctx, d):
            continue
        out.append(_signature_dict(r))
    return out


def complete_signature(
    session: Session, ctx: OrganisationContext, sig_id: uuid.UUID, body: SignatureConsent
) -> dict[str, Any]:
    from app.managed_documents.schemas import SIGN_ACK_PHRASE

    md_access.require_sign_complete(ctx)
    r = session.get(ManagedDocumentSignatureRequest, sig_id)
    if r is None or r.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Signature request not found")
    if r.signer_user_id != ctx.user_id:
        raise HTTPException(status_code=403, detail="Not the designated signer")
    if r.status != "pending_signature":
        raise HTTPException(status_code=409, detail="Not pending")
    if r.expires_at and r.expires_at < NOW():
        r.status = "expired"
        session.flush()
        raise HTTPException(status_code=409, detail="Expired")
    if body.acknowledgement.strip() != SIGN_ACK_PHRASE:
        raise HTTPException(status_code=400, detail="Acknowledgement phrase mismatch")

    r.status = "signed"
    r.signed_at = NOW()
    r.signature_evidence = {
        "kind": "internal_acknowledgement",
        "consent_at": NOW().isoformat(),
        "consent_text": body.consent_text,
        "version_id": str(r.version_id),
        "disclaimer": "In-platform record only — not a qualified electronic signature under UK/eIDAS trust services.",
    }
    _audit(session, ctx, audit_events.DOCUMENT_SIGN_COMPLETE, "managed_document_signature", r.id, "Signature recorded")
    session.flush()
    return {"id": str(r.id), "status": r.status}


def decline_signature(session: Session, ctx: OrganisationContext, sig_id: uuid.UUID, body: SignatureDecline) -> dict[str, Any]:
    md_access.require_sign_complete(ctx)
    r = session.get(ManagedDocumentSignatureRequest, sig_id)
    if r is None or r.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Signature request not found")
    if r.signer_user_id != ctx.user_id:
        raise HTTPException(status_code=403, detail="Not the designated signer")
    if r.status != "pending_signature":
        raise HTTPException(status_code=409, detail="Not pending")
    r.status = "declined"
    r.declined_at = NOW()
    r.decline_reason = body.reason
    _audit(session, ctx, audit_events.DOCUMENT_SIGN_DECLINE, "managed_document_signature", r.id, "Signature declined")
    session.flush()
    return {"id": str(r.id), "status": r.status}


def dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    md_access.require_meta(ctx)
    docs = list(
        session.scalars(select(ManagedDocument).where(ManagedDocument.organisation_id == ctx.organisation_id))
    )
    visible = [d for d in docs if md_access.document_visible(session, ctx, d)]
    settings = md_access.get_or_create_settings(session, ctx.organisation_id)
    expiring = sum(1 for d in visible if compute_expiry_tracking(d, settings) == "expiring_soon")
    expired = sum(1 for d in visible if compute_expiry_tracking(d, settings) == "expired")
    pending_rev = sum(1 for d in visible if d.retention_status == "pending_review")
    pending_access = session.scalar(
        select(func.count())
        .select_from(ManagedDocumentAccessRequest)
        .where(
            ManagedDocumentAccessRequest.organisation_id == ctx.organisation_id,
            ManagedDocumentAccessRequest.status.in_(["submitted", "under_review"]),
        )
    ) or 0
    pending_sig = session.scalar(
        select(func.count())
        .select_from(ManagedDocumentSignatureRequest)
        .where(
            ManagedDocumentSignatureRequest.organisation_id == ctx.organisation_id,
            ManagedDocumentSignatureRequest.status == "pending_signature",
        )
    ) or 0
    by_cat: dict[str, int] = {}
    for d in visible:
        cat = session.get(ManagedDocumentCategory, d.category_id)
        code = cat.code if cat else "unknown"
        by_cat[code] = by_cat.get(code, 0) + 1
    recent_sorted = sorted(visible, key=lambda x: x.updated_at or _MIN_UTC, reverse=True)[:10]
    return {
        "total_documents": len(visible),
        "by_category": by_cat,
        "expiring_soon": expiring,
        "expired": expired,
        "pending_retention_review": pending_rev,
        "pending_access_requests": pending_access,
        "pending_signatures": pending_sig,
        "recently_updated": [_doc_dict(session, d) for d in recent_sorted],
    }
