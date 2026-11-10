"""F2.1 Support caseload, daily log, and handover APIs."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.idempotency.deps import IdempotencyKey
from app.idempotency.service import SCOPE_DAILY_LOG_CREATE, apply_idempotent, fresh_or_replay, jsonable
from app.support import service as support_service
from app.daily_log_rewrite import service as rewrite_service
from app.support.schemas import (
    CaseAssignmentCreate,
    CaseAssignmentOut,
    DailyLogCreate,
    DailyLogOut,
    DailyLogRewriteIn,
    DailyLogRewriteOut,
    DailyLogUpdate,
    HandoverCreate,
    HandoverOut,
    HandoverUpdate,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter()
caseload_router = APIRouter(prefix="/caseload", tags=["support-caseload"])
logs_router = APIRouter(prefix="/daily-logs", tags=["support-daily-logs"])
handovers_router = APIRouter(prefix="/handovers", tags=["support-handovers"])
assignments_router = APIRouter(prefix="/case-assignments", tags=["support-assignments"])


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@caseload_router.get("", response_model=dict[str, Any])
def list_caseload(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    status_filter: str = Query("active", alias="status"),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items, total = support_service.list_caseload(
        session, org, page=page, page_size=page_size, q=q, status_filter=status_filter
    )
    return _page(
        [CaseAssignmentOut.model_validate(item).model_dump(mode="json") for item in items],
        page,
        page_size,
        total,
    )


@caseload_router.get("/tenants/{tenant_id}", response_model=dict[str, Any])
def get_case_detail(
    tenant_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    detail = support_service.get_case_detail(session, org, tenant_id)
    detail["recent_logs"] = [
        DailyLogOut.model_validate(row).model_dump(mode="json") for row in detail["recent_logs"]
    ]
    detail["recent_handovers"] = [
        HandoverOut.model_validate(row).model_dump(mode="json")
        for row in detail["recent_handovers"]
    ]
    detail["assignments"] = [
        CaseAssignmentOut.model_validate(row).model_dump(mode="json")
        for row in detail["assignments"]
    ]
    return detail


@assignments_router.post("", response_model=CaseAssignmentOut, status_code=201)
def create_assignment(
    body: CaseAssignmentCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.create_assignment(session, org, body)


@assignments_router.post("/{assignment_id}/end", response_model=CaseAssignmentOut)
def end_assignment(
    assignment_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.end_assignment(session, org, assignment_id)


@logs_router.post("", response_model=DailyLogOut, status_code=201)
def create_daily_log(
    body: DailyLogCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    idempotency_key: IdempotencyKey,
) -> Any:
    holder: dict[str, Any] = {}

    def produce() -> tuple[Any, dict[str, Any]]:
        row = support_service.create_daily_log(session, org, body)
        holder["row"] = row
        return row.id, jsonable(DailyLogOut.model_validate(row).model_dump(mode="json"))

    result = apply_idempotent(
        session,
        organisation_id=org.organisation_id,
        user_id=org.user_id,
        scope=SCOPE_DAILY_LOG_CREATE,
        key=idempotency_key,
        resource_type="daily_log",
        success_status=201,
        produce=produce,
    )
    return fresh_or_replay(result, holder.get("row"))


@logs_router.post("/rewrite", response_model=DailyLogRewriteOut)
def rewrite_daily_log(
    body: DailyLogRewriteIn,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    """Rewrite draft text. Does not create a daily log."""
    return rewrite_service.rewrite_daily_log_draft(
        session, org, text=body.text, tenant_id=body.tenant_id
    )


@logs_router.get("", response_model=dict[str, Any])
def list_daily_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = support_service.list_daily_logs(
        session, org, tenant_id=tenant_id, page=page, page_size=page_size
    )
    return _page(
        [DailyLogOut.model_validate(row).model_dump(mode="json") for row in rows],
        page,
        page_size,
        total,
    )


@logs_router.get("/{log_id}", response_model=DailyLogOut)
def get_daily_log(
    log_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.get_daily_log(session, org, log_id)


@logs_router.patch("/{log_id}", response_model=DailyLogOut)
def update_daily_log(
    log_id: uuid.UUID,
    body: DailyLogUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.update_daily_log(session, org, log_id, body)


@handovers_router.post("", response_model=HandoverOut, status_code=201)
def create_handover(
    body: HandoverCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.create_handover(session, org, body)


@handovers_router.get("", response_model=dict[str, Any])
def list_handovers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    pending_only: bool = Query(False),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = support_service.list_handovers(
        session,
        org,
        tenant_id=tenant_id,
        status_filter=status_filter,
        pending_only=pending_only,
        page=page,
        page_size=page_size,
    )
    return _page(
        [HandoverOut.model_validate(row).model_dump(mode="json") for row in rows],
        page,
        page_size,
        total,
    )


@handovers_router.get("/{handover_id}", response_model=HandoverOut)
def get_handover(
    handover_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.get_handover(session, org, handover_id)


@handovers_router.patch("/{handover_id}", response_model=HandoverOut)
def patch_handover(
    handover_id: uuid.UUID,
    body: HandoverUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.update_handover_draft(session, org, handover_id, body)


@handovers_router.post("/{handover_id}/submit", response_model=HandoverOut)
def submit_handover(
    handover_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.transition_handover(
        session, org, handover_id, target_status="submitted"
    )


@handovers_router.post("/{handover_id}/acknowledge", response_model=HandoverOut)
def acknowledge_handover(
    handover_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.transition_handover(
        session, org, handover_id, target_status="acknowledged"
    )


@handovers_router.post("/{handover_id}/complete", response_model=HandoverOut)
def complete_handover(
    handover_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.transition_handover(
        session, org, handover_id, target_status="completed"
    )


@handovers_router.post("/{handover_id}/cancel", response_model=HandoverOut)
def cancel_handover(
    handover_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return support_service.transition_handover(
        session, org, handover_id, target_status="cancelled"
    )


router.include_router(caseload_router)
router.include_router(assignments_router)
router.include_router(logs_router)
router.include_router(handovers_router)
