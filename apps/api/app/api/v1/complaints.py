"""F2.7 complaints workflow APIs."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.complaints import service as complaint_service
from app.complaints.schemas import (
    AssignRequest,
    AssociateFileRequest,
    CategoryCreate,
    CategoryOut,
    ComplaintCreate,
    ComplaintOut,
    ComplaintUpdate,
    DashboardOut,
    DeadlineUpdateRequest,
    EscalateRequest,
    EscalationOut,
    HistoryEventOut,
    NoteCreate,
    NoteOut,
    PriorityRequest,
    ResolveEscalationRequest,
    StatusTransitionRequest,
)
from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/complaints", tags=["complaints"])


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/dashboard", response_model=DashboardOut)
def complaints_dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return complaint_service.dashboard_stats(session, org)


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return complaint_service.list_categories(session, org)


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(
    body: CategoryCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return complaint_service.create_category(session, org, body)


@router.post("/seed-defaults", response_model=dict[str, str])
def seed_defaults(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    complaint_service.ensure_defaults(session, org)
    return {"status": "ok"}


@router.post("/escalations/{escalation_id}/resolve", response_model=EscalationOut)
def resolve_escalation(
    escalation_id: uuid.UUID,
    body: ResolveEscalationRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return complaint_service.resolve_escalation(session, org, escalation_id, body)


@router.post("", response_model=ComplaintOut, status_code=201)
def create_complaint(
    body: ComplaintCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = complaint_service.create_complaint(session, org, body)
    return complaint_service.complaint_out_dict(session, org, row)


@router.get("", response_model=dict[str, Any])
def list_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    overdue_only: bool = Query(False),
    escalated_only: bool = Query(False),
    q: str | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = complaint_service.list_complaints(
        session,
        org,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        priority=priority,
        overdue_only=overdue_only,
        escalated_only=escalated_only,
        q=q,
    )
    return _page(
        [complaint_service.complaint_out_dict(session, org, row) for row in rows],
        page,
        page_size,
        total,
    )


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(
    complaint_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = complaint_service.get_complaint(session, org, complaint_id)
    return complaint_service.complaint_out_dict(session, org, row)


@router.patch("/{complaint_id}", response_model=ComplaintOut)
def patch_complaint(
    complaint_id: uuid.UUID,
    body: ComplaintUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = complaint_service.update_complaint(session, org, complaint_id, body)
    return complaint_service.complaint_out_dict(session, org, row)


@router.post("/{complaint_id}/assign", response_model=ComplaintOut)
def assign_complaint(
    complaint_id: uuid.UUID,
    body: AssignRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = complaint_service.assign_complaint(session, org, complaint_id, body)
    return complaint_service.complaint_out_dict(session, org, row)


@router.post("/{complaint_id}/priority", response_model=ComplaintOut)
def change_priority(
    complaint_id: uuid.UUID,
    body: PriorityRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = complaint_service.change_priority(session, org, complaint_id, body)
    return complaint_service.complaint_out_dict(session, org, row)


@router.post("/{complaint_id}/transition", response_model=ComplaintOut)
def transition(
    complaint_id: uuid.UUID,
    body: StatusTransitionRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = complaint_service.transition_status(session, org, complaint_id, body)
    return complaint_service.complaint_out_dict(session, org, row)


@router.post("/{complaint_id}/notes", response_model=NoteOut, status_code=201)
def add_note(
    complaint_id: uuid.UUID,
    body: NoteCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return complaint_service.add_note(session, org, complaint_id, body)


@router.get("/{complaint_id}/notes", response_model=list[NoteOut])
def list_notes(
    complaint_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return complaint_service.list_notes(session, org, complaint_id)


@router.post("/{complaint_id}/deadlines", response_model=ComplaintOut)
def update_deadlines(
    complaint_id: uuid.UUID,
    body: DeadlineUpdateRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = complaint_service.update_deadlines(session, org, complaint_id, body)
    return complaint_service.complaint_out_dict(session, org, row)


@router.post("/{complaint_id}/escalate", response_model=EscalationOut, status_code=201)
def escalate(
    complaint_id: uuid.UUID,
    body: EscalateRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return complaint_service.escalate_complaint(session, org, complaint_id, body)


@router.get("/{complaint_id}/escalations", response_model=list[EscalationOut])
def list_escalations(
    complaint_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return complaint_service.list_escalations(session, org, complaint_id)


@router.get("/{complaint_id}/history", response_model=list[HistoryEventOut])
def history(
    complaint_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return complaint_service.list_history(session, org, complaint_id)


@router.post("/{complaint_id}/files", response_model=ComplaintOut)
def associate_file(
    complaint_id: uuid.UUID,
    body: AssociateFileRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = complaint_service.associate_file(session, org, complaint_id, body)
    return complaint_service.complaint_out_dict(session, org, row)
