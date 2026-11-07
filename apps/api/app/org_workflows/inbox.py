"""Aggregated organisation approvals inbox (no duplicate approval records)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.complaints import Complaint
from app.db.models.evidence import EvidenceChecklistItem
from app.db.models.housing import HousingApplication
from app.db.models.maintenance import MaintenanceRequest
from app.db.models.managed_documents import ManagedDocument, ManagedDocumentAccessRequest
from app.db.models.org_workflows import OrganisationApprovalAssignment, OrganisationCustomFormSubmission
from app.org_workflows.access import require_inbox_read
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext

PENDING_HOUSING = frozenset({"submitted", "under_review", "information_required"})
PENDING_DOC_ACCESS = frozenset({"submitted", "under_review"})
PENDING_FORM = frozenset({"pending", "under_review", "additional_information_required"})
PENDING_COMPLAINT = frozenset({"submitted", "awaiting_information", "reopened"})
PENDING_EVIDENCE = frozenset({"under_review"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assignments_map(session: Session, org_id: uuid.UUID) -> dict[tuple[str, uuid.UUID], uuid.UUID]:
    rows = session.scalars(
        select(OrganisationApprovalAssignment).where(OrganisationApprovalAssignment.organisation_id == org_id)
    ).all()
    return {(r.source_type, r.source_id): r.reviewer_user_id for r in rows}


def _can_collect(authz, permission: Permission) -> bool:
    return authz.has_permission(permission)


def _item(
    *,
    reference: str,
    source_type: str,
    source_id: uuid.UUID,
    title: str,
    status: str,
    priority: str | None,
    requester_user_id: uuid.UUID | None,
    reviewer_user_id: uuid.UUID | None,
    submitted_at: datetime | None,
    related_url_path: str | None,
    is_overdue: bool = False,
) -> dict[str, Any]:
    return {
        "reference": reference,
        "source_type": source_type,
        "source_id": str(source_id),
        "title": title,
        "status": status,
        "priority": priority,
        "requester_user_id": str(requester_user_id) if requester_user_id else None,
        "reviewer_user_id": str(reviewer_user_id) if reviewer_user_id else None,
        "submitted_at": submitted_at.isoformat() if submitted_at else None,
        "is_overdue": is_overdue,
        "related_url_path": related_url_path,
    }


def collect_inbox_items(
    session: Session,
    ctx: OrganisationContext,
    *,
    status_filter: str | None = None,
    source_type: str | None = None,
    q: str | None = None,
    include_completed: bool = False,
) -> list[dict[str, Any]]:
    require_inbox_read(ctx)
    items: list[dict[str, Any]] = []
    assign = _assignments_map(session, ctx.organisation_id)
    authz = ctx.authorization

    if source_type in (None, "housing_application") and _can_collect(authz, Permission.APPLICATIONS_REVIEW):
        stmt = select(HousingApplication).where(HousingApplication.organisation_id == ctx.organisation_id)
        if include_completed:
            stmt = stmt.where(
                HousingApplication.status.in_(
                    tuple(PENDING_HOUSING | {"approved", "rejected", "withdrawn", "closed"})
                )
            )
        else:
            stmt = stmt.where(HousingApplication.status.in_(tuple(PENDING_HOUSING)))
        if status_filter:
            stmt = stmt.where(HousingApplication.status == status_filter)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(HousingApplication.reference_number.ilike(like))
        for row in session.scalars(stmt).all():
            reviewer = row.reviewer_user_id or assign.get(("housing_application", row.id))
            items.append(
                _item(
                    reference=row.reference_number,
                    source_type="housing_application",
                    source_id=row.id,
                    title=f"Housing application {row.reference_number}",
                    status=row.status,
                    priority=row.priority,
                    requester_user_id=None,
                    reviewer_user_id=reviewer,
                    submitted_at=row.submitted_at or row.created_at,
                    related_url_path=f"/dashboard/housing-applications/{row.id}",
                )
            )

    if source_type in (None, "managed_document_access") and _can_collect(authz, Permission.DOCUMENTS_ACCESS_APPROVE):
        stmt = (
            select(ManagedDocumentAccessRequest, ManagedDocument.title)
            .join(ManagedDocument, ManagedDocument.id == ManagedDocumentAccessRequest.document_id)
            .where(ManagedDocumentAccessRequest.organisation_id == ctx.organisation_id)
        )
        if include_completed:
            stmt = stmt.where(
                ManagedDocumentAccessRequest.status.in_(
                    tuple(PENDING_DOC_ACCESS | {"approved", "rejected", "withdrawn", "expired"})
                )
            )
        else:
            stmt = stmt.where(ManagedDocumentAccessRequest.status.in_(tuple(PENDING_DOC_ACCESS)))
        if status_filter:
            stmt = stmt.where(ManagedDocumentAccessRequest.status == status_filter)
        for req, doc_title in session.execute(stmt).all():
            ref = f"DOC-ACC-{str(req.id)[:8].upper()}"
            if q and q.lower() not in ref.lower():
                continue
            reviewer = assign.get(("managed_document_access", req.id))
            items.append(
                _item(
                    reference=ref,
                    source_type="managed_document_access",
                    source_id=req.id,
                    title=f"Document access: {doc_title}",
                    status=req.status,
                    priority=None,
                    requester_user_id=req.requester_user_id,
                    reviewer_user_id=reviewer,
                    submitted_at=req.created_at,
                    related_url_path="/dashboard/documents",
                )
            )

    if source_type in (None, "maintenance_request") and _can_collect(authz, Permission.MAINTENANCE_APPROVE):
        stmt = select(MaintenanceRequest).where(
            MaintenanceRequest.organisation_id == ctx.organisation_id,
            MaintenanceRequest.requires_approval.is_(True),
        )
        if include_completed:
            stmt = stmt.where(MaintenanceRequest.status.in_(("awaiting_approval", "approved", "rejected")))
        else:
            stmt = stmt.where(MaintenanceRequest.status == "awaiting_approval")
        if q:
            like = f"%{q}%"
            stmt = stmt.where(MaintenanceRequest.reference_number.ilike(like))
        for row in session.scalars(stmt).all():
            st = row.approval_status or ("pending" if row.status == "awaiting_approval" else row.status)
            reviewer = assign.get(("maintenance_request", row.id))
            items.append(
                _item(
                    reference=row.reference_number,
                    source_type="maintenance_request",
                    source_id=row.id,
                    title=row.title,
                    status=st if st != "pending" else "pending",
                    priority=row.priority,
                    requester_user_id=None,
                    reviewer_user_id=reviewer,
                    submitted_at=row.created_at,
                    related_url_path=f"/dashboard/maintenance/{row.id}",
                )
            )

    if source_type in (None, "custom_form_submission") and _can_collect(
        authz, Permission.ORGANISATION_FORMS_SUBMISSIONS_REVIEW
    ):
        stmt = select(OrganisationCustomFormSubmission).where(
            OrganisationCustomFormSubmission.organisation_id == ctx.organisation_id
        )
        if include_completed:
            stmt = stmt.where(
                OrganisationCustomFormSubmission.status.in_(
                    tuple(PENDING_FORM | {"approved", "rejected", "cancelled", "expired"})
                )
            )
        else:
            stmt = stmt.where(OrganisationCustomFormSubmission.status.in_(tuple(PENDING_FORM)))
        if status_filter:
            stmt = stmt.where(OrganisationCustomFormSubmission.status == status_filter)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(OrganisationCustomFormSubmission.reference_number.ilike(like))
        for row in session.scalars(stmt).all():
            items.append(
                _item(
                    reference=row.reference_number,
                    source_type="custom_form_submission",
                    source_id=row.id,
                    title=f"Form submission {row.reference_number}",
                    status=row.status,
                    priority=None,
                    requester_user_id=row.submitter_user_id,
                    reviewer_user_id=row.assigned_reviewer_user_id,
                    submitted_at=row.submitted_at or row.created_at,
                    related_url_path=f"/dashboard/org-workflows/submissions/{row.id}",
                )
            )

    if source_type in (None, "complaint") and _can_collect(authz, Permission.COMPLAINTS_MANAGE):
        stmt = select(Complaint).where(Complaint.organisation_id == ctx.organisation_id)
        if include_completed:
            stmt = stmt.where(Complaint.status.in_(tuple(PENDING_COMPLAINT | {"resolved", "closed", "escalated"})))
        else:
            stmt = stmt.where(Complaint.status.in_(tuple(PENDING_COMPLAINT)))
        for row in session.scalars(stmt).all():
            ref = row.reference_number
            if q and q.lower() not in ref.lower() and q.lower() not in row.title.lower():
                continue
            reviewer = row.assigned_user_id or assign.get(("complaint", row.id))
            items.append(
                _item(
                    reference=ref,
                    source_type="complaint",
                    source_id=row.id,
                    title=row.title,
                    status=row.status,
                    priority=row.priority,
                    requester_user_id=row.submitted_by_user_id,
                    reviewer_user_id=reviewer,
                    submitted_at=row.created_at,
                    related_url_path=f"/dashboard/complaints/{row.id}",
                )
            )

    if source_type in (None, "evidence_item") and _can_collect(authz, Permission.EVIDENCE_REVIEW):
        stmt = select(EvidenceChecklistItem).where(
            EvidenceChecklistItem.organisation_id == ctx.organisation_id,
        )
        if include_completed:
            stmt = stmt.where(
                EvidenceChecklistItem.status.in_(tuple(PENDING_EVIDENCE | {"accepted", "rejected", "missing"}))
            )
        else:
            stmt = stmt.where(EvidenceChecklistItem.status.in_(tuple(PENDING_EVIDENCE)))
        for row in session.scalars(stmt).all():
            ref = f"EVD-{str(row.id)[:8].upper()}"
            if q and q.lower() not in ref.lower() and q.lower() not in row.title.lower():
                continue
            reviewer = assign.get(("evidence_item", row.id))
            items.append(
                _item(
                    reference=ref,
                    source_type="evidence_item",
                    source_id=row.id,
                    title=row.title,
                    status=row.status,
                    priority=None,
                    requester_user_id=None,
                    reviewer_user_id=reviewer,
                    submitted_at=row.updated_at,
                    related_url_path="/dashboard/housing-applications",
                )
            )

    items.sort(key=lambda x: x.get("submitted_at") or "", reverse=True)
    return items


def paginate(items: list[dict[str, Any]], page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    total = len(items)
    start = (page - 1) * page_size
    return items[start : start + page_size], total
