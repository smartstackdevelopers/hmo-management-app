"""F2.10 structured support plans API."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.db.models.enums import HMoreRole
from app.support_plans import access as sp_access
from app.support_plans import service as sp_service
from app.support_plans.schemas import (
    ExportCreate,
    GoalAchieveBody,
    GoalCancelBody,
    GoalCreate,
    GoalProgressNoteCreate,
    GoalUpdate,
    MilestoneCancelBody,
    MilestoneCompleteBody,
    MilestoneCreate,
    MilestoneUpdate,
    PlanTransitionBody,
    ReviewCreate,
    ReviewUpdate,
    SupportPlanCreate,
    SupportPlanReviseCreate,
    SupportPlanUpdate,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/tenants/{tenant_id}/support-plans", tags=["support-plans"])


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


# --- Plan lifecycle ---


@router.post("", response_model=dict[str, Any], status_code=201)
def create_support_plan(
    tenant_id: uuid.UUID,
    body: SupportPlanCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.create_plan(session, org, body)


@router.get("", response_model=dict[str, Any])
def list_support_plans(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, max_length=32),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items, total = sp_service.list_plans(
        session, org, tenant_id, page=page, page_size=page_size, status_filter=status
    )
    return _page(items, page, page_size, total)


@router.get("/{plan_id}", response_model=dict[str, Any])
def get_support_plan(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.get_plan(session, org, tenant_id, plan_id)


@router.patch("/{plan_id}", response_model=dict[str, Any])
def patch_support_plan(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    body: SupportPlanUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.update_plan(session, org, tenant_id, plan_id, body)


@router.post("/{plan_id}/activate", response_model=dict[str, Any])
def activate_support_plan(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.activate_plan(session, org, tenant_id, plan_id)


@router.post("/{plan_id}/hold", response_model=dict[str, Any])
def hold_support_plan(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    body: PlanTransitionBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.hold_plan(session, org, tenant_id, plan_id, body)


@router.post("/{plan_id}/resume", response_model=dict[str, Any])
def resume_support_plan(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.resume_plan(session, org, tenant_id, plan_id)


@router.post("/{plan_id}/review-start", response_model=dict[str, Any])
def review_start_support_plan(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.start_plan_review(session, org, tenant_id, plan_id)


@router.post("/{plan_id}/complete", response_model=dict[str, Any])
def complete_support_plan(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.complete_plan(session, org, tenant_id, plan_id)


@router.post("/{plan_id}/close", response_model=dict[str, Any])
def close_support_plan(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.close_plan(session, org, tenant_id, plan_id)


@router.post("/{plan_id}/revise", response_model=dict[str, Any], status_code=201)
def revise_support_plan(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    body: SupportPlanReviseCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.revise_plan(session, org, tenant_id, plan_id, body)


@router.get("/{plan_id}/history", response_model=list[Any])
def support_plan_history(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return sp_service.plan_history(session, org, tenant_id, plan_id)


@router.get("/{plan_id}/progress-history", response_model=list[Any])
def support_plan_progress_history(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return sp_service.combined_progress_history(session, org, tenant_id, plan_id)


# --- Goals ---


@router.post("/{plan_id}/goals", response_model=dict[str, Any], status_code=201)
def create_goal_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    body: GoalCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.create_goal(session, org, tenant_id, plan_id, body)


@router.get("/{plan_id}/goals", response_model=list[Any])
def list_goals_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return sp_service.list_goals(session, org, tenant_id, plan_id)


@router.get("/{plan_id}/goals/{goal_id}", response_model=dict[str, Any])
def get_goal_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.get_goal(session, org, tenant_id, plan_id, goal_id)


@router.patch("/{plan_id}/goals/{goal_id}", response_model=dict[str, Any])
def patch_goal_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: GoalUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.update_goal(session, org, tenant_id, plan_id, goal_id, body)


@router.post("/{plan_id}/goals/{goal_id}/progress-notes", response_model=dict[str, Any], status_code=201)
def add_goal_progress_note_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: GoalProgressNoteCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.add_goal_progress_note(session, org, tenant_id, plan_id, goal_id, body)


@router.get("/{plan_id}/goals/{goal_id}/progress-notes", response_model=list[Any])
def list_goal_progress_notes_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return sp_service.list_goal_progress_notes(session, org, tenant_id, plan_id, goal_id)


@router.post("/{plan_id}/goals/{goal_id}/achieve", response_model=dict[str, Any])
def achieve_goal_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: GoalAchieveBody | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.achieve_goal(
        session, org, tenant_id, plan_id, goal_id, body or GoalAchieveBody()
    )


@router.post("/{plan_id}/goals/{goal_id}/cancel", response_model=dict[str, Any])
def cancel_goal_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: GoalCancelBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.cancel_goal(session, org, tenant_id, plan_id, goal_id, body)


@router.get("/{plan_id}/goals/{goal_id}/changes", response_model=list[Any])
def goal_change_history_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return sp_service.goal_change_history(session, org, tenant_id, plan_id, goal_id)


# --- Milestones ---


@router.post("/{plan_id}/goals/{goal_id}/milestones", response_model=dict[str, Any], status_code=201)
def create_milestone_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: MilestoneCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.create_milestone(session, org, tenant_id, plan_id, goal_id, body)


@router.get("/{plan_id}/goals/{goal_id}/milestones", response_model=list[Any])
def list_milestones_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return sp_service.list_milestones(session, org, tenant_id, plan_id, goal_id)


@router.patch("/{plan_id}/goals/{goal_id}/milestones/{milestone_id}", response_model=dict[str, Any])
def patch_milestone_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: MilestoneUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.update_milestone(session, org, tenant_id, plan_id, goal_id, milestone_id, body)


@router.post("/{plan_id}/goals/{goal_id}/milestones/{milestone_id}/complete", response_model=dict[str, Any])
def complete_milestone_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: MilestoneCompleteBody | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.complete_milestone(
        session, org, tenant_id, plan_id, goal_id, milestone_id, body or MilestoneCompleteBody()
    )


@router.post("/{plan_id}/goals/{goal_id}/milestones/{milestone_id}/cancel", response_model=dict[str, Any])
def cancel_milestone_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: MilestoneCancelBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.cancel_milestone(session, org, tenant_id, plan_id, goal_id, milestone_id, body)


@router.get("/{plan_id}/goals/{goal_id}/milestones/{milestone_id}/changes", response_model=list[Any])
def milestone_history_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    goal_id: uuid.UUID,
    milestone_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return sp_service.milestone_history(session, org, tenant_id, plan_id, goal_id, milestone_id)


# --- Reviews ---


@router.post("/{plan_id}/reviews", response_model=dict[str, Any], status_code=201)
def create_review_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    body: ReviewCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.create_review(session, org, tenant_id, plan_id, body)


@router.get("/{plan_id}/reviews", response_model=dict[str, Any])
def list_reviews_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    review_type: str | None = Query(None, max_length=16),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items, total = sp_service.list_reviews(
        session, org, tenant_id, plan_id, page=page, page_size=page_size, review_type=review_type
    )
    return _page(items, page, page_size, total)


@router.get("/{plan_id}/reviews/{review_id}", response_model=dict[str, Any])
def get_review_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    review_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.get_review(session, org, tenant_id, plan_id, review_id)


@router.patch("/{plan_id}/reviews/{review_id}", response_model=dict[str, Any])
def patch_review_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    review_id: uuid.UUID,
    body: ReviewUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.update_review(session, org, tenant_id, plan_id, review_id, body)


@router.post("/{plan_id}/reviews/{review_id}/finalise", response_model=dict[str, Any])
def finalise_review_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    review_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.finalise_review(session, org, tenant_id, plan_id, review_id)


@router.get("/{plan_id}/reviews-history", response_model=list[Any])
def review_history_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    return sp_service.review_history(session, org, tenant_id, plan_id)


# --- Exports ---


@router.post("/{plan_id}/exports", response_model=dict[str, Any], status_code=201)
def create_export_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    body: ExportCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.create_progress_export(session, org, tenant_id, plan_id, body)


@router.get("/{plan_id}/exports", response_model=dict[str, Any])
def list_exports_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items, total = sp_service.list_progress_exports(
        session, org, tenant_id, plan_id, page=page, page_size=page_size
    )
    return _page(items, page, page_size, total)


@router.get("/{plan_id}/exports/{export_id}", response_model=dict[str, Any])
def get_export_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    export_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.get_export_metadata(session, org, tenant_id, plan_id, export_id)


@router.get("/{plan_id}/exports/{export_id}/download")
def download_export_route(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    export_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    fmeta, data, filename = sp_service.download_export(session, org, tenant_id, plan_id, export_id)
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=data,
        media_type=fmeta.content_type,
        headers={
            "Content-Disposition": disposition,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


tenant_self_router = APIRouter(prefix="/tenant/support-plans", tags=["support-plans"])


@tenant_self_router.get("", response_model=dict[str, Any])
def list_own_support_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, max_length=32),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    if org.role != HMoreRole.TENANT:
        raise HTTPException(status_code=403, detail="Tenant role required")
    tid = sp_access.resolve_own_tenant_id(session, org)
    if tid is None:
        raise HTTPException(status_code=404, detail="No linked tenant profile")
    items, total = sp_service.list_plans(
        session, org, tid, page=page, page_size=page_size, status_filter=status
    )
    return _page(items, page, page_size, total)


@tenant_self_router.get("/{plan_id}", response_model=dict[str, Any])
def get_own_support_plan(
    plan_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    if org.role != HMoreRole.TENANT:
        raise HTTPException(status_code=403, detail="Tenant role required")
    tid = sp_access.resolve_own_tenant_id(session, org)
    if tid is None:
        raise HTTPException(status_code=404, detail="No linked tenant profile")
    return sp_service.get_plan(session, org, tid, plan_id)


dash_router = APIRouter(prefix="/support-plans/dashboard", tags=["support-plans"])


@dash_router.get("", response_model=dict[str, Any])
def progress_dashboard_route(
    tenant_id: uuid.UUID | None = Query(None),
    worker_user_id: uuid.UUID | None = Query(None),
    plan_status: str | None = Query(None, max_length=32),
    review_period_start: date | None = Query(None),
    review_period_end: date | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return sp_service.progress_dashboard(
        session,
        org,
        tenant_id=tenant_id,
        worker_user_id=worker_user_id,
        plan_status=plan_status,
        review_period_start=review_period_start,
        review_period_end=review_period_end,
    )
