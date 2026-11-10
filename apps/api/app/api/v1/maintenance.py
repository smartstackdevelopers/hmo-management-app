"""F2.8 maintenance and repairs APIs."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.idempotency.deps import IdempotencyKey
from app.idempotency.service import (
    SCOPE_MAINTENANCE_COMPLETE,
    SCOPE_MAINTENANCE_CREATE,
    SCOPE_MAINTENANCE_NOTE,
    SCOPE_MAINTENANCE_TRANSITION,
    SCOPE_MAINTENANCE_UPDATE,
    apply_idempotent,
    fresh_or_replay,
    jsonable,
)
from app.maintenance import service as maintenance_service
from app.maintenance.access import assert_can_access_maintenance_photo
from app.maintenance.schemas import (
    ApprovalDecisionRequest,
    AssociatePhotoRequest,
    AssignRequest,
    CategoryCreate,
    CategoryOut,
    CompleteRequest,
    DashboardOut,
    EmergencyContentOut,
    EmergencyContentUpdate,
    HistoryEventOut,
    MaintenanceCreate,
    MaintenanceOut,
    MaintenanceUpdate,
    NoteCreate,
    NoteOut,
    PriorityRequest,
    RequestFileOut,
    ScheduleVisitRequest,
    StatusTransitionRequest,
    VisitCancelRequest,
    VisitCompleteRequest,
    VisitOut,
    VisitRescheduleRequest,
)
from app.db.session import get_session
from app.storage import service as file_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/dashboard", response_model=DashboardOut)
def maintenance_dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return maintenance_service.dashboard_stats(session, org)


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return maintenance_service.list_categories(session, org)


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(
    body: CategoryCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return maintenance_service.create_category(session, org, body)


@router.post("/seed-defaults", response_model=dict[str, str])
def seed_defaults(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    maintenance_service.ensure_defaults(session, org)
    return {"status": "ok"}


@router.post("", response_model=MaintenanceOut, status_code=201)
def create_maintenance(
    body: MaintenanceCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    idempotency_key: IdempotencyKey,
) -> Any:
    holder: dict[str, Any] = {}

    def produce() -> tuple[Any, dict[str, Any]]:
        row = maintenance_service.create_request(session, org, body)
        payload = maintenance_service.request_out_dict(session, org, row)
        holder["row"] = payload
        return row.id, jsonable(payload)

    result = apply_idempotent(
        session,
        organisation_id=org.organisation_id,
        user_id=org.user_id,
        scope=SCOPE_MAINTENANCE_CREATE,
        key=idempotency_key,
        resource_type="maintenance_request",
        success_status=201,
        produce=produce,
    )
    return fresh_or_replay(result, holder.get("row"))


@router.get("", response_model=dict[str, Any])
def list_maintenance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    property_id: uuid.UUID | None = Query(None),
    pending_approval: bool = Query(False),
    q: str | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = maintenance_service.list_requests(
        session,
        org,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        priority=priority,
        property_id=property_id,
        pending_approval=pending_approval,
        q=q,
    )
    return _page(
        [maintenance_service.request_out_dict(session, org, row) for row in rows],
        page,
        page_size,
        total,
    )


@router.get("/emergency/{kind}", response_model=EmergencyContentOut)
def get_emergency_instructions(
    kind: str,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = maintenance_service.emergency_content(session, org, kind)
    if row is None:
        return EmergencyContentOut(
            kind=kind,
            title="",
            body="",
            requires_formal_approval=True,
            approved_for_use=False,
        )
    return EmergencyContentOut(
        kind=row.kind,
        title=row.title,
        body=row.body,
        requires_formal_approval=row.requires_formal_approval,
        approved_for_use=row.approved_for_use,
    )


@router.put("/emergency/{kind}", response_model=EmergencyContentOut)
def put_emergency_instructions(
    kind: str,
    body: EmergencyContentUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = maintenance_service.update_emergency_content(session, org, kind, body)
    return EmergencyContentOut(
        kind=row.kind,
        title=row.title,
        body=row.body,
        requires_formal_approval=row.requires_formal_approval,
        approved_for_use=row.approved_for_use,
    )


@router.get("/{request_id}", response_model=MaintenanceOut)
def get_maintenance(
    request_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = maintenance_service.get_request(session, org, request_id)
    return maintenance_service.request_out_dict(session, org, row)


@router.patch("/{request_id}", response_model=MaintenanceOut)
def patch_maintenance(
    request_id: uuid.UUID,
    body: MaintenanceUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    idempotency_key: IdempotencyKey,
) -> Any:
    holder: dict[str, Any] = {}

    def produce() -> tuple[Any, dict[str, Any]]:
        row = maintenance_service.update_request(session, org, request_id, body)
        payload = maintenance_service.request_out_dict(session, org, row)
        holder["row"] = payload
        return row.id, jsonable(payload)

    result = apply_idempotent(
        session,
        organisation_id=org.organisation_id,
        user_id=org.user_id,
        scope=f"{SCOPE_MAINTENANCE_UPDATE}:{request_id}",
        key=idempotency_key,
        resource_type="maintenance_request",
        success_status=200,
        produce=produce,
    )
    return fresh_or_replay(result, holder.get("row"))


@router.post("/{request_id}/assign", response_model=MaintenanceOut)
def assign_maintenance(
    request_id: uuid.UUID,
    body: AssignRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = maintenance_service.assign_request(session, org, request_id, body)
    return maintenance_service.request_out_dict(session, org, row)


@router.post("/{request_id}/priority", response_model=MaintenanceOut)
def priority_maintenance(
    request_id: uuid.UUID,
    body: PriorityRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = maintenance_service.change_priority(session, org, request_id, body)
    return maintenance_service.request_out_dict(session, org, row)


@router.post("/{request_id}/transition", response_model=MaintenanceOut)
def transition_maintenance(
    request_id: uuid.UUID,
    body: StatusTransitionRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    idempotency_key: IdempotencyKey,
) -> Any:
    holder: dict[str, Any] = {}

    def produce() -> tuple[Any, dict[str, Any]]:
        row = maintenance_service.transition_status(session, org, request_id, body)
        payload = maintenance_service.request_out_dict(session, org, row)
        holder["row"] = payload
        return row.id, jsonable(payload)

    result = apply_idempotent(
        session,
        organisation_id=org.organisation_id,
        user_id=org.user_id,
        scope=f"{SCOPE_MAINTENANCE_TRANSITION}:{request_id}",
        key=idempotency_key,
        resource_type="maintenance_request",
        success_status=200,
        produce=produce,
    )
    return fresh_or_replay(result, holder.get("row"))


@router.post("/{request_id}/approval", response_model=MaintenanceOut)
def approval_maintenance(
    request_id: uuid.UUID,
    body: ApprovalDecisionRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = maintenance_service.record_approval(session, org, request_id, body)
    return maintenance_service.request_out_dict(session, org, row)


@router.post("/{request_id}/schedule", response_model=VisitOut)
def schedule_maintenance(
    request_id: uuid.UUID,
    body: ScheduleVisitRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return maintenance_service.schedule_visit(session, org, request_id, body)


@router.post("/{request_id}/visits/{visit_id}/reschedule", response_model=VisitOut)
def reschedule_maintenance_visit(
    request_id: uuid.UUID,
    visit_id: uuid.UUID,
    body: VisitRescheduleRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return maintenance_service.reschedule_visit(session, org, request_id, visit_id, body)


@router.post("/{request_id}/visits/{visit_id}/cancel", response_model=VisitOut)
def cancel_maintenance_visit(
    request_id: uuid.UUID,
    visit_id: uuid.UUID,
    body: VisitCancelRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return maintenance_service.cancel_visit(session, org, request_id, visit_id, body)


@router.post("/{request_id}/visits/{visit_id}/complete", response_model=VisitOut)
def complete_maintenance_visit(
    request_id: uuid.UUID,
    visit_id: uuid.UUID,
    body: VisitCompleteRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return maintenance_service.complete_visit(session, org, request_id, visit_id, body)


@router.get("/{request_id}/visits", response_model=list[VisitOut])
def list_maintenance_visits(
    request_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return maintenance_service.list_visits(session, org, request_id)


@router.post("/{request_id}/notes", response_model=NoteOut, status_code=201)
def add_maintenance_note(
    request_id: uuid.UUID,
    body: NoteCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    idempotency_key: IdempotencyKey,
) -> Any:
    holder: dict[str, Any] = {}

    def produce() -> tuple[Any, dict[str, Any]]:
        row = maintenance_service.add_note(session, org, request_id, body)
        holder["row"] = row
        return row.id, jsonable(NoteOut.model_validate(row).model_dump(mode="json"))

    result = apply_idempotent(
        session,
        organisation_id=org.organisation_id,
        user_id=org.user_id,
        scope=f"{SCOPE_MAINTENANCE_NOTE}:{request_id}",
        key=idempotency_key,
        resource_type="maintenance_note",
        success_status=201,
        produce=produce,
    )
    return fresh_or_replay(result, holder.get("row"))


@router.get("/{request_id}/notes", response_model=list[NoteOut])
def list_maintenance_notes(
    request_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return maintenance_service.list_notes(session, org, request_id)


@router.get("/{request_id}/history", response_model=list[HistoryEventOut])
def maintenance_history(
    request_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return maintenance_service.list_history(session, org, request_id)


@router.get("/{request_id}/files", response_model=list[RequestFileOut])
def list_maintenance_files(
    request_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    rows = maintenance_service.list_request_files(session, org, request_id)
    return [
        RequestFileOut(
            file_id=r.file_id,
            caption=r.caption,
            photo_kind=r.photo_kind,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{request_id}/files", response_model=MaintenanceOut)
def associate_maintenance_file(
    request_id: uuid.UUID,
    body: AssociatePhotoRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = maintenance_service.associate_photo(session, org, request_id, body)
    return maintenance_service.request_out_dict(session, org, row)


@router.post("/{request_id}/files/upload", response_model=MaintenanceOut)
async def upload_maintenance_photo(
    request_id: uuid.UUID,
    upload: UploadFile = File(...),
    caption: str | None = Form(default=None, max_length=500),
    photo_kind: str = Form(default="problem", max_length=32),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    data = await upload.read()
    row = maintenance_service.upload_photo(
        session,
        org,
        request_id,
        filename=upload.filename,
        content_type=upload.content_type,
        data=data,
        caption=caption,
        photo_kind=photo_kind,
    )
    return maintenance_service.request_out_dict(session, org, row)


@router.get("/{request_id}/files/{file_id}/content")
def download_maintenance_file(
    request_id: uuid.UUID,
    file_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    assert_can_access_maintenance_photo(session, org, request_id, file_id)
    row, data = file_service.download_file(session, org, file_id)
    disposition = f"attachment; filename*=UTF-8''{quote(row.original_filename)}"
    return Response(
        content=data,
        media_type=row.content_type,
        headers={
            "Content-Disposition": disposition,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/{request_id}/complete", response_model=MaintenanceOut)
def complete_maintenance(
    request_id: uuid.UUID,
    body: CompleteRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    idempotency_key: IdempotencyKey,
) -> Any:
    holder: dict[str, Any] = {}

    def produce() -> tuple[Any, dict[str, Any]]:
        row = maintenance_service.complete_request(session, org, request_id, body)
        payload = maintenance_service.request_out_dict(session, org, row)
        holder["row"] = payload
        return row.id, jsonable(payload)

    result = apply_idempotent(
        session,
        organisation_id=org.organisation_id,
        user_id=org.user_id,
        scope=f"{SCOPE_MAINTENANCE_COMPLETE}:{request_id}",
        key=idempotency_key,
        resource_type="maintenance_request",
        success_status=200,
        produce=produce,
    )
    return fresh_or_replay(result, holder.get("row"))
