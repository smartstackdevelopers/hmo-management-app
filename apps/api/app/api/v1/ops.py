"""F2.2 rota, visits, tasks, and reminder APIs."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.idempotency.deps import IdempotencyKey
from app.idempotency.service import (
    SCOPE_TASK_UPDATE,
    SCOPE_VISIT_UPDATE,
    apply_idempotent,
    fresh_or_replay,
    jsonable,
)
from app.ops import service as ops_service
from app.ops.schemas import (
    ReminderOut,
    ShiftCancel,
    ShiftConflictCheck,
    ShiftConflictResult,
    ShiftCreate,
    ShiftOut,
    ShiftUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
    VisitCreate,
    VisitOut,
    VisitUpdate,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter()
shifts_router = APIRouter(prefix="/shifts", tags=["rota-shifts"])
visits_router = APIRouter(prefix="/visits", tags=["tenant-visits"])
tasks_router = APIRouter(prefix="/tasks", tags=["operational-tasks"])
reminders_router = APIRouter(prefix="/reminders", tags=["reminders"])


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@shifts_router.post("/conflicts", response_model=ShiftConflictResult)
def check_shift_conflicts(
    body: ShiftConflictCheck,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return ops_service.check_shift_conflicts(session, org, body)


@shifts_router.post("", response_model=ShiftOut, status_code=201)
def create_shift(
    body: ShiftCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return ops_service.create_shift(session, org, body)


@shifts_router.get("", response_model=dict[str, Any])
def list_shifts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    staff_user_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = ops_service.list_shifts(
        session,
        org,
        page=page,
        page_size=page_size,
        staff_user_id=staff_user_id,
        date_from=date_from,
        date_to=date_to,
    )
    return _page(
        [ShiftOut.model_validate(row).model_dump(mode="json") for row in rows],
        page,
        page_size,
        total,
    )


@shifts_router.get("/{shift_id}", response_model=ShiftOut)
def get_shift(
    shift_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return ops_service.get_shift(session, org, shift_id)


@shifts_router.patch("/{shift_id}", response_model=ShiftOut)
def patch_shift(
    shift_id: uuid.UUID,
    body: ShiftUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return ops_service.update_shift(session, org, shift_id, body)


@shifts_router.post("/{shift_id}/cancel", response_model=ShiftOut)
def cancel_shift(
    shift_id: uuid.UUID,
    body: ShiftCancel,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return ops_service.cancel_shift(session, org, shift_id, body)


@visits_router.post("", response_model=VisitOut, status_code=201)
def create_visit(
    body: VisitCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return ops_service.create_visit(session, org, body)


@visits_router.get("", response_model=dict[str, Any])
def list_visits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    upcoming_only: bool = Query(False),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = ops_service.list_visits(
        session,
        org,
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
        status_filter=status_filter,
        upcoming_only=upcoming_only,
    )
    return _page(
        [VisitOut.model_validate(row).model_dump(mode="json") for row in rows],
        page,
        page_size,
        total,
    )


@visits_router.get("/{visit_id}", response_model=VisitOut)
def get_visit(
    visit_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return ops_service.get_visit(session, org, visit_id)


@visits_router.patch("/{visit_id}", response_model=VisitOut)
def patch_visit(
    visit_id: uuid.UUID,
    body: VisitUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    idempotency_key: IdempotencyKey,
) -> Any:
    holder: dict[str, Any] = {}

    def produce() -> tuple[Any, dict[str, Any]]:
        row = ops_service.update_visit(session, org, visit_id, body)
        holder["row"] = row
        return row.id, jsonable(VisitOut.model_validate(row).model_dump(mode="json"))

    result = apply_idempotent(
        session,
        organisation_id=org.organisation_id,
        user_id=org.user_id,
        scope=f"{SCOPE_VISIT_UPDATE}:{visit_id}",
        key=idempotency_key,
        resource_type="tenant_visit",
        success_status=200,
        produce=produce,
    )
    return fresh_or_replay(result, holder.get("row"))


@tasks_router.post("", response_model=TaskOut, status_code=201)
def create_task(
    body: TaskCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    row = ops_service.create_task(session, org, body)
    return ops_service.task_out_dict(row)


@tasks_router.get("", response_model=dict[str, Any])
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    assigned_user_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    overdue_only: bool = Query(False),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = ops_service.list_tasks(
        session,
        org,
        page=page,
        page_size=page_size,
        assigned_user_id=assigned_user_id,
        status_filter=status_filter,
        priority=priority,
        overdue_only=overdue_only,
    )
    return _page([ops_service.task_out_dict(row) for row in rows], page, page_size, total)


@tasks_router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return ops_service.task_out_dict(ops_service.get_task(session, org, task_id))


@tasks_router.patch("/{task_id}", response_model=TaskOut)
def patch_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    idempotency_key: IdempotencyKey,
) -> Any:
    holder: dict[str, Any] = {}

    def produce() -> tuple[Any, dict[str, Any]]:
        payload = ops_service.task_out_dict(ops_service.update_task(session, org, task_id, body))
        holder["row"] = payload
        return payload["id"], jsonable(payload)

    result = apply_idempotent(
        session,
        organisation_id=org.organisation_id,
        user_id=org.user_id,
        scope=f"{SCOPE_TASK_UPDATE}:{task_id}",
        key=idempotency_key,
        resource_type="operational_task",
        success_status=200,
        produce=produce,
    )
    return fresh_or_replay(result, holder.get("row"))


@reminders_router.get("", response_model=dict[str, Any])
def list_reminders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = ops_service.list_reminders(
        session, org, page=page, page_size=page_size, status_filter=status_filter
    )
    return _page(
        [ReminderOut.model_validate(row).model_dump(mode="json") for row in rows],
        page,
        page_size,
        total,
    )


router.include_router(shifts_router)
router.include_router(visits_router)
router.include_router(tasks_router)
router.include_router(reminders_router)
