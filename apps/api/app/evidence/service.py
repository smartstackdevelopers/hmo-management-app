"""F2.6 evidence checklist and pack generation services."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.evidence import (
    EvidenceChecklistItem,
    EvidenceChecklistTemplate,
    EvidenceItemFile,
    EvidencePack,
    EvidenceReviewHistory,
)
from app.db.models.file_metadata import FileMetadata
from app.evidence import access
from app.evidence.pdf import build_simple_pdf
from app.evidence.schemas import (
    AssociateFileRequest,
    ChecklistItemCreate,
    ChecklistItemUpdate,
    GeneratePackRequest,
    TemplateCreate,
)
from app.housing.service import get_application
from app.storage import service as file_service
from app.tenancy.context import OrganisationContext

EVIDENCE_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"received", "missing", "not_applicable", "under_review"}),
    "received": frozenset({"under_review", "accepted", "rejected", "missing"}),
    "under_review": frozenset({"accepted", "rejected", "missing", "received"}),
    "accepted": frozenset({"under_review"}),
    "rejected": frozenset({"received", "under_review", "missing"}),
    "missing": frozenset({"received", "not_applicable", "under_review"}),
    "not_applicable": frozenset({"pending"}),
}

DEFAULT_TEMPLATE_SEED = (
    ("id_proof", "Proof of identity", "identity", True, 10),
    ("address_proof", "Proof of address", "address", True, 20),
    ("income_proof", "Income / benefits evidence", "finance", False, 30),
    ("support_letter", "Support worker letter", "support", False, 40),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(
    session: Session,
    ctx: OrganisationContext,
    *,
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


def _item_file_ids(session: Session, item_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        session.scalars(
            select(EvidenceItemFile.file_id).where(EvidenceItemFile.checklist_item_id == item_id)
        ).all()
    )


def item_out_dict(session: Session, row: EvidenceChecklistItem) -> dict[str, Any]:
    return {
        "id": row.id,
        "organisation_id": row.organisation_id,
        "application_id": row.application_id,
        "category": row.category,
        "title": row.title,
        "description": row.description,
        "is_required": row.is_required,
        "status": row.status,
        "reviewer_notes": row.reviewer_notes,
        "rejection_reason": row.rejection_reason,
        "submitted_at": row.submitted_at,
        "reviewed_at": row.reviewed_at,
        "reviewed_by_user_id": row.reviewed_by_user_id,
        "created_by_user_id": row.created_by_user_id,
        "sort_order": row.sort_order,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "file_ids": _item_file_ids(session, row.id),
    }


def ensure_default_templates(session: Session, ctx: OrganisationContext) -> list[EvidenceChecklistTemplate]:
    access.require_evidence_manage(ctx)
    existing = list(
        session.scalars(
            select(EvidenceChecklistTemplate).where(
                EvidenceChecklistTemplate.organisation_id == ctx.organisation_id
            )
        ).all()
    )
    if existing:
        return existing
    rows: list[EvidenceChecklistTemplate] = []
    for code, title, category, required, order in DEFAULT_TEMPLATE_SEED:
        row = EvidenceChecklistTemplate(
            organisation_id=ctx.organisation_id,
            code=code,
            title=title,
            category=category,
            description="Organisation-configurable default — not a statutory requirement.",
            is_required=required,
            sort_order=order,
            is_active=True,
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return rows


def create_template(
    session: Session, ctx: OrganisationContext, data: TemplateCreate
) -> EvidenceChecklistTemplate:
    access.require_evidence_manage(ctx)
    row = EvidenceChecklistTemplate(
        organisation_id=ctx.organisation_id,
        code=data.code,
        title=data.title,
        category=data.category,
        description=data.description,
        is_required=data.is_required,
        sort_order=data.sort_order,
        is_active=True,
    )
    session.add(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.EVIDENCE_TEMPLATE_CREATE,
        resource_type="evidence_checklist_template",
        resource_id=row.id,
        summary="Evidence checklist template created",
        metadata={"code": row.code},
    )
    return row


def seed_checklist_from_templates(
    session: Session, ctx: OrganisationContext, application_id: uuid.UUID
) -> list[EvidenceChecklistItem]:
    application = get_application(session, ctx, application_id)
    access.require_evidence_manage(ctx)
    ensure_default_templates(session, ctx)
    existing_count = (
        session.scalar(
            select(func.count())
            .select_from(EvidenceChecklistItem)
            .where(
                EvidenceChecklistItem.organisation_id == ctx.organisation_id,
                EvidenceChecklistItem.application_id == application.id,
            )
        )
        or 0
    )
    if existing_count:
        return list_checklist(session, ctx, application.id)
    templates = session.scalars(
        select(EvidenceChecklistTemplate)
        .where(
            EvidenceChecklistTemplate.organisation_id == ctx.organisation_id,
            EvidenceChecklistTemplate.is_active.is_(True),
        )
        .order_by(EvidenceChecklistTemplate.sort_order.asc())
    ).all()
    rows: list[EvidenceChecklistItem] = []
    for tmpl in templates:
        row = EvidenceChecklistItem(
            organisation_id=ctx.organisation_id,
            application_id=application.id,
            template_id=tmpl.id,
            category=tmpl.category,
            title=tmpl.title,
            description=tmpl.description,
            is_required=tmpl.is_required,
            status="pending",
            created_by_user_id=ctx.user_id,
            sort_order=tmpl.sort_order,
        )
        session.add(row)
        rows.append(row)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.EVIDENCE_CHECKLIST_SEED,
        resource_type="housing_application",
        resource_id=application.id,
        summary="Evidence checklist seeded from organisation templates",
        metadata={"count": len(rows)},
    )
    return rows


def create_checklist_item(
    session: Session,
    ctx: OrganisationContext,
    application_id: uuid.UUID,
    data: ChecklistItemCreate,
) -> EvidenceChecklistItem:
    application = get_application(session, ctx, application_id)
    access.require_evidence_manage(ctx)
    row = EvidenceChecklistItem(
        organisation_id=ctx.organisation_id,
        application_id=application.id,
        category=data.category,
        title=data.title,
        description=data.description,
        is_required=data.is_required,
        status="pending",
        created_by_user_id=ctx.user_id,
        sort_order=data.sort_order,
    )
    session.add(row)
    session.flush()
    _record_history(session, ctx, row, from_status=None, to_status="pending", note="Created")
    _audit(
        session,
        ctx,
        action=audit_events.EVIDENCE_ITEM_CREATE,
        resource_type="evidence_checklist_item",
        resource_id=row.id,
        summary="Evidence checklist item created",
        metadata={"application_id": str(application.id)},
    )
    return row


def list_checklist(
    session: Session, ctx: OrganisationContext, application_id: uuid.UUID
) -> list[EvidenceChecklistItem]:
    get_application(session, ctx, application_id)
    access.require_evidence_read(ctx)
    return list(
        session.scalars(
            select(EvidenceChecklistItem)
            .where(
                EvidenceChecklistItem.organisation_id == ctx.organisation_id,
                EvidenceChecklistItem.application_id == application_id,
            )
            .order_by(EvidenceChecklistItem.sort_order.asc(), EvidenceChecklistItem.created_at.asc())
        ).all()
    )


def get_checklist_item(
    session: Session, ctx: OrganisationContext, item_id: uuid.UUID
) -> EvidenceChecklistItem:
    access.require_evidence_read(ctx)
    row = session.get(EvidenceChecklistItem, item_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found")
    get_application(session, ctx, row.application_id)
    return row


def _record_history(
    session: Session,
    ctx: OrganisationContext,
    item: EvidenceChecklistItem,
    *,
    from_status: str | None,
    to_status: str,
    note: str | None = None,
) -> None:
    session.add(
        EvidenceReviewHistory(
            organisation_id=ctx.organisation_id,
            checklist_item_id=item.id,
            from_status=from_status,
            to_status=to_status,
            changed_by_user_id=ctx.user_id,
            note=note,
        )
    )


def update_checklist_item(
    session: Session,
    ctx: OrganisationContext,
    item_id: uuid.UUID,
    data: ChecklistItemUpdate,
) -> EvidenceChecklistItem:
    row = get_checklist_item(session, ctx, item_id)
    payload = data.model_dump(exclude_unset=True)
    target_status = payload.pop("status", None)
    rejection_reason = payload.pop("rejection_reason", None)
    reviewer_notes = payload.pop("reviewer_notes", None)
    if payload:
        access.require_evidence_manage(ctx)
        for key, value in payload.items():
            setattr(row, key, value)
    if reviewer_notes is not None:
        access.require_evidence_review(ctx)
        row.reviewer_notes = reviewer_notes

    if target_status is not None and target_status != row.status:
        access.require_evidence_review(ctx)
        allowed = EVIDENCE_TRANSITIONS.get(row.status, frozenset())
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition evidence from {row.status} to {target_status}",
            )
        if target_status == "rejected":
            reason = rejection_reason or row.rejection_reason
            if not reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="rejection_reason is required when rejecting evidence",
                )
            row.rejection_reason = reason
        prev = row.status
        row.status = target_status
        row.reviewed_at = _now()
        row.reviewed_by_user_id = ctx.user_id
        if target_status == "received" and row.submitted_at is None:
            row.submitted_at = _now()
        _record_history(
            session,
            ctx,
            row,
            from_status=prev,
            to_status=target_status,
            note=(rejection_reason or data.reviewer_notes or "")[:500] or None,
        )
        _audit(
            session,
            ctx,
            action=audit_events.EVIDENCE_ITEM_REVIEW,
            resource_type="evidence_checklist_item",
            resource_id=row.id,
            summary=f"Evidence status {prev} → {target_status}",
            metadata={"from": prev, "to": target_status},
        )
    elif rejection_reason is not None:
        access.require_evidence_review(ctx)
        row.rejection_reason = rejection_reason
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.EVIDENCE_ITEM_UPDATE,
        resource_type="evidence_checklist_item",
        resource_id=row.id,
        summary="Evidence checklist item updated",
    )
    return row


def associate_file(
    session: Session,
    ctx: OrganisationContext,
    item_id: uuid.UUID,
    data: AssociateFileRequest,
) -> EvidenceChecklistItem:
    row = get_checklist_item(session, ctx, item_id)
    access.require_evidence_manage(ctx)
    meta = session.get(FileMetadata, data.file_id)
    if meta is None or meta.organisation_id != ctx.organisation_id or meta.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    # Bind file to application for traceability via F1.8 resource fields.
    meta.resource_type = "housing_application"
    meta.resource_id = str(row.application_id)
    existing = session.scalar(
        select(EvidenceItemFile).where(
            EvidenceItemFile.checklist_item_id == row.id,
            EvidenceItemFile.file_id == data.file_id,
        )
    )
    if existing is None:
        session.add(
            EvidenceItemFile(
                organisation_id=ctx.organisation_id,
                checklist_item_id=row.id,
                file_id=data.file_id,
                associated_by_user_id=ctx.user_id,
            )
        )
    if row.status == "pending":
        prev = row.status
        row.status = "received"
        row.submitted_at = row.submitted_at or _now()
        _record_history(session, ctx, row, from_status=prev, to_status="received", note="File associated")
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.EVIDENCE_FILE_ASSOCIATE,
        resource_type="evidence_checklist_item",
        resource_id=row.id,
        summary="Evidence file associated",
        metadata={"file_id": str(data.file_id)},
    )
    return row


def upload_and_associate(
    session: Session,
    ctx: OrganisationContext,
    item_id: uuid.UUID,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
) -> EvidenceChecklistItem:
    """Upload via F1.8 private storage then associate (for roles without FILES_MANAGE)."""
    row = get_checklist_item(session, ctx, item_id)
    access.require_evidence_manage(ctx)
    stored = file_service.upload_file(
        session,
        ctx,
        filename=filename,
        declared_content_type=content_type,
        data=data,
        resource_type="housing_application",
        resource_id=str(row.application_id),
    )
    return associate_file(
        session, ctx, item_id, AssociateFileRequest(file_id=uuid.UUID(stored["id"]))
    )


def list_templates(
    session: Session, ctx: OrganisationContext
) -> list[EvidenceChecklistTemplate]:
    access.require_evidence_read(ctx)
    return list(
        session.scalars(
            select(EvidenceChecklistTemplate)
            .where(
                EvidenceChecklistTemplate.organisation_id == ctx.organisation_id,
                EvidenceChecklistTemplate.is_active.is_(True),
            )
            .order_by(EvidenceChecklistTemplate.sort_order.asc())
        ).all()
    )


def download_pack_bytes(
    session: Session, ctx: OrganisationContext, pack_id: uuid.UUID
) -> tuple[EvidencePack, bytes, str, str]:
    """Return pack, PDF bytes, content type, and safe filename after access checks."""
    pack = get_pack(session, ctx, pack_id)
    if pack.file_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pack file missing")
    meta, content = file_service.download_file(session, ctx, pack.file_id)
    _audit(
        session,
        ctx,
        action=audit_events.EVIDENCE_PACK_DOWNLOAD,
        resource_type="evidence_pack",
        resource_id=pack.id,
        summary="Evidence pack downloaded",
        metadata={"file_id": str(pack.file_id)},
    )
    filename = meta.original_filename or f"evidence-pack-{pack.id}.pdf"
    return pack, content, meta.content_type or "application/pdf", filename


def list_review_history(
    session: Session, ctx: OrganisationContext, item_id: uuid.UUID
) -> list[EvidenceReviewHistory]:
    get_checklist_item(session, ctx, item_id)
    return list(
        session.scalars(
            select(EvidenceReviewHistory)
            .where(
                EvidenceReviewHistory.organisation_id == ctx.organisation_id,
                EvidenceReviewHistory.checklist_item_id == item_id,
            )
            .order_by(EvidenceReviewHistory.created_at.asc())
        ).all()
    )


def readiness(session: Session, ctx: OrganisationContext, application_id: uuid.UUID) -> dict[str, Any]:
    items = list_checklist(session, ctx, application_id)
    required = [i for i in items if i.is_required]
    outstanding = [
        {"id": str(i.id), "title": i.title, "status": i.status}
        for i in required
        if i.status not in {"accepted", "not_applicable"}
    ]
    accepted = sum(1 for i in required if i.status == "accepted")
    complete = len(required) > 0 and len(outstanding) == 0
    return {
        "application_id": application_id,
        "ready": complete,
        "is_complete": complete,
        "required_total": len(required),
        "required_accepted": accepted,
        "outstanding": outstanding,
    }


def generate_pack(
    session: Session,
    ctx: OrganisationContext,
    application_id: uuid.UUID,
    data: GeneratePackRequest,
) -> EvidencePack:
    access.require_pack_generate(ctx)
    application = get_application(session, ctx, application_id)
    items = list_checklist(session, ctx, application_id)
    ready = readiness(session, ctx, application_id)
    if not ready["is_complete"] and not data.allow_incomplete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Evidence pack incomplete — outstanding required items remain",
                "outstanding": ready["outstanding"],
            },
        )

    lines = [
        f"Application: {application.reference_number}",
        f"Generated at (UTC): {_now().isoformat()}",
        f"Generated by user: {ctx.user_id}",
        f"Pack complete: {'yes' if ready['is_complete'] else 'NO — incomplete draft'}",
        "",
        "Housing requirements:",
        (application.housing_requirements or "")[:500],
        "",
        "Evidence checklist:",
    ]
    for item in items:
        flag = "REQUIRED" if item.is_required else "optional"
        lines.append(f"- [{item.status}] ({flag}) {item.title}")
        if item.status == "rejected" and item.rejection_reason:
            lines.append(f"  Rejection reason recorded (see application system).")
        file_ids = _item_file_ids(session, item.id)
        if file_ids:
            lines.append(f"  Linked files: {len(file_ids)}")
    if ready["outstanding"]:
        lines.append("")
        lines.append("OUTSTANDING REQUIRED EVIDENCE:")
        for o in ready["outstanding"]:
            lines.append(f"- {o['title']} ({o['status']})")
    lines.append("")
    lines.append(
        "Note: This pack is an operational export. It is not a certified council form "
        "and does not assert statutory completeness."
    )

    pdf_bytes = build_simple_pdf(
        title=f"Evidence Pack {application.reference_number}",
        lines=lines,
    )
    stored = file_service.upload_file(
        session,
        ctx,
        filename=f"evidence-pack-{application.reference_number}.pdf",
        declared_content_type="application/pdf",
        data=pdf_bytes,
        resource_type="evidence_pack",
        resource_id=str(application.id),
    )
    pack = EvidencePack(
        organisation_id=ctx.organisation_id,
        application_id=application.id,
        generated_by_user_id=ctx.user_id,
        file_id=uuid.UUID(stored["id"]),
        status="ready" if ready["is_complete"] else "incomplete_draft",
        is_complete=bool(ready["is_complete"]),
        outstanding_summary=(
            None
            if ready["is_complete"]
            else "; ".join(o["title"] for o in ready["outstanding"])[:2000]
        ),
        generated_at=_now(),
    )
    session.add(pack)
    session.flush()
    _audit(
        session,
        ctx,
        action=audit_events.EVIDENCE_PACK_GENERATE,
        resource_type="evidence_pack",
        resource_id=pack.id,
        summary="Evidence pack generated",
        metadata={
            "application_id": str(application.id),
            "is_complete": pack.is_complete,
            "file_id": stored["id"],
        },
    )
    return pack


def list_packs(
    session: Session, ctx: OrganisationContext, application_id: uuid.UUID
) -> list[EvidencePack]:
    get_application(session, ctx, application_id)
    access.require_evidence_read(ctx)
    return list(
        session.scalars(
            select(EvidencePack)
            .where(
                EvidencePack.organisation_id == ctx.organisation_id,
                EvidencePack.application_id == application_id,
            )
            .order_by(EvidencePack.generated_at.desc())
        ).all()
    )


def get_pack(session: Session, ctx: OrganisationContext, pack_id: uuid.UUID) -> EvidencePack:
    access.require_evidence_read(ctx)
    pack = session.get(EvidencePack, pack_id)
    if pack is None or pack.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence pack not found")
    get_application(session, ctx, pack.application_id)
    return pack
