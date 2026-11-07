"""Delegate approval decisions to authorised source-module services."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.housing import HousingApplication
from app.db.models.org_workflows import OrganisationApprovalAssignment, OrganisationCustomFormSubmission
from app.housing import service as housing_service
from app.housing.schemas import DecisionCreate, InformationRequiredRequest
from app.maintenance import service as maintenance_service
from app.maintenance.schemas import ApprovalDecisionRequest
from app.managed_documents import service as md_service
from app.managed_documents.schemas import AccessRequestDecide
from app.org_workflows import notify
from app.org_workflows.access import require_approval_assign, require_approval_decide
from app.org_workflows.schemas import ApprovalDecide, AssignReviewer
from app.tenancy.context import OrganisationContext

SUBMISSION_TRANSITIONS = {
    "pending": frozenset({"under_review", "additional_information_required", "approved", "rejected", "cancelled"}),
    "under_review": frozenset({"additional_information_required", "approved", "rejected"}),
    "additional_information_required": frozenset({"pending", "under_review", "cancelled"}),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(
    session: Session,
    ctx: OrganisationContext,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    summary: str,
    metadata: dict | None = None,
) -> None:
    record_event(
        session,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=summary,
        metadata=metadata or {},
        raise_on_error=False,
    )


def assign_reviewer(
    session: Session,
    ctx: OrganisationContext,
    source_type: str,
    source_id: uuid.UUID,
    body: AssignReviewer,
) -> dict:
    require_approval_assign(ctx)
    if source_type == "housing_application":
        row = session.get(HousingApplication, source_id)
        if row is None or row.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=404, detail="Not found")
        row.reviewer_user_id = body.reviewer_user_id
    else:
        existing = session.scalar(
            select(OrganisationApprovalAssignment).where(
                OrganisationApprovalAssignment.organisation_id == ctx.organisation_id,
                OrganisationApprovalAssignment.source_type == source_type,
                OrganisationApprovalAssignment.source_id == source_id,
            )
        )
        if existing:
            existing.reviewer_user_id = body.reviewer_user_id
            existing.assigned_by_user_id = ctx.user_id
            existing.assigned_at = _now()
        else:
            session.add(
                OrganisationApprovalAssignment(
                    organisation_id=ctx.organisation_id,
                    source_type=source_type,
                    source_id=source_id,
                    reviewer_user_id=body.reviewer_user_id,
                    assigned_by_user_id=ctx.user_id,
                    assigned_at=_now(),
                )
            )
        if source_type == "custom_form_submission":
            sub = session.get(OrganisationCustomFormSubmission, source_id)
            if sub and sub.organisation_id == ctx.organisation_id:
                sub.assigned_reviewer_user_id = body.reviewer_user_id
    _audit(
        session,
        ctx,
        audit_events.ORG_APPROVAL_ASSIGNED,
        source_type,
        source_id,
        "Reviewer assigned",
        {"reviewer_user_id": str(body.reviewer_user_id)},
    )
    notify.approval_assigned(session, ctx, body.reviewer_user_id, source_type, source_id)
    session.flush()
    return {"source_type": source_type, "source_id": str(source_id), "reviewer_user_id": str(body.reviewer_user_id)}


def decide_approval(
    session: Session,
    ctx: OrganisationContext,
    source_type: str,
    source_id: uuid.UUID,
    body: ApprovalDecide,
) -> dict:
    require_approval_decide(ctx)
    if body.action == "request_information" and not (body.reason and body.reason.strip()):
        raise HTTPException(status_code=400, detail="Reason required")

    if source_type == "housing_application":
        if body.action == "request_information":
            housing_service.request_information(
                session, ctx, source_id, InformationRequiredRequest(notes=body.reason or "")
            )
            result = {"status": "information_required"}
        else:
            if body.action == "reject" and not body.reason:
                raise HTTPException(status_code=400, detail="Rejection requires a reason")
            decision = "approved" if body.action == "approve" else "rejected"
            housing_service.record_decision(
                session,
                ctx,
                source_id,
                DecisionCreate(
                    decision=decision,
                    decision_notes=body.reason or "Approved",
                    add_to_waiting_list=body.housing_add_to_waiting_list,
                ),
            )
            result = {"decision": decision}
        notify.approval_decided(session, ctx, source_type, source_id, body.action)
        return result

    if source_type == "managed_document_access":
        if body.action == "request_information":
            raise HTTPException(status_code=400, detail="Use document module for this action")
        approve = body.action == "approve"
        md_service.decide_access_request(
            session,
            ctx,
            source_id,
            AccessRequestDecide(
                approve=approve,
                decision_reason=body.reason,
                temporary_hours=body.maintenance_temporary_hours or 72,
            ),
        )
        notify.approval_decided(session, ctx, source_type, source_id, body.action)
        return {"decision": "approved" if approve else "rejected"}

    if source_type == "maintenance_request":
        if body.action == "request_information":
            raise HTTPException(status_code=400, detail="Not supported for maintenance approval gate")
        decision = "approved" if body.action == "approve" else "rejected"
        maintenance_service.record_approval(
            session,
            ctx,
            source_id,
            ApprovalDecisionRequest(decision=decision, reason=body.reason),
        )
        notify.approval_decided(session, ctx, source_type, source_id, body.action)
        return {"decision": decision}

    if source_type == "custom_form_submission":
        sub = session.get(OrganisationCustomFormSubmission, source_id)
        if sub is None or sub.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=404, detail="Submission not found")
        allowed = SUBMISSION_TRANSITIONS.get(sub.status, frozenset())
        if body.action == "approve":
            target = "approved"
        elif body.action == "reject":
            target = "rejected"
        else:
            target = "additional_information_required"
        if target not in allowed:
            raise HTTPException(status_code=409, detail="Invalid submission transition")
        if body.action == "reject" and not body.reason:
            raise HTTPException(status_code=400, detail="Rejection requires a reason")
        sub.status = target
        sub.decision_notes = body.reason
        sub.decided_by_user_id = ctx.user_id
        sub.decided_at = _now()
        _audit(session, ctx, audit_events.ORG_FORM_SUBMISSION_DECIDE, "org_custom_form_submission", sub.id, target)
        notify.approval_decided(session, ctx, source_type, source_id, body.action)
        session.flush()
        return {"status": sub.status}

    if source_type in {"complaint", "evidence_item"}:
        raise HTTPException(
            status_code=400,
            detail="Open the source record to complete this action; inbox is read-only for this type",
        )

    raise HTTPException(status_code=400, detail="Unknown source type")
