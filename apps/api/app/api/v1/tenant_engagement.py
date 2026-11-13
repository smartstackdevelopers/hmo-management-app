"""F8.8 optional tenant engagement API."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenant_engagement import service
from app.tenant_engagement.service import _settings
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/tenant-engagement", tags=["tenant-engagement"])


class SettingsBody(BaseModel):
    enabled: bool | None = None
    privacy_review_complete: bool | None = None
    points_enabled: bool | None = None
    leaderboard_enabled: bool | None = None
    ai_assistant_enabled: bool | None = None
    point_rules: dict[str, Any] | None = None
    reminder_config: dict[str, Any] | None = None


class GoalBody(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_slug: str
    start_date: date | None = None
    target_date: date | None = None
    tenant_user_id: uuid.UUID | None = None


class MilestoneBody(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    target_date: date | None = None


class MilestoneCompleteBody(BaseModel):
    evidence_file_id: uuid.UUID | None = None
    review_notes: str | None = None


class BadgeAwardBody(BaseModel):
    tenant_user_id: uuid.UUID
    verified: bool = True


class LeaderboardBody(BaseModel):
    opted_in: bool
    display_name: str | None = Field(default=None, max_length=64)


class AiBody(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)


@router.get("/settings")
def get_settings_api(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.TENANT_ENGAGEMENT_READ)
    return service.settings_dict(_settings(session, ctx.organisation_id))


@router.patch("/settings")
def patch_settings_api(
    body: SettingsBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.update_settings(session, ctx, body.model_dump(exclude_unset=True))
    return service.settings_dict(row)


@router.post("/goals")
def create_goal_api(body: GoalBody, session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    g = service.create_goal(session, ctx, body.model_dump())
    return {"id": str(g.id), "title": g.title, "progress_status": g.progress_status}


@router.post("/goals/{goal_id}/milestones")
def add_milestone_api(
    goal_id: uuid.UUID,
    body: MilestoneBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    ms = service.add_milestone(session, ctx, goal_id, body.model_dump())
    return {"id": str(ms.id), "status": ms.status}


@router.post("/milestones/{milestone_id}/complete")
def complete_milestone_api(
    milestone_id: uuid.UUID,
    body: MilestoneCompleteBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    ms = service.complete_milestone(session, ctx, milestone_id, body.model_dump())
    return {"id": str(ms.id), "status": ms.status}


@router.post("/badges/{badge_id}/award")
def award_badge_api(
    badge_id: uuid.UUID,
    body: BadgeAwardBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.award_badge(session, ctx, badge_id, body.tenant_user_id, verified=body.verified)
    return {"id": str(row.id), "verified": row.verified}


@router.post("/activities/{activity_id}/complete")
def complete_activity_api(
    activity_id: uuid.UUID,
    tenant_user_id: uuid.UUID | None = Query(default=None),
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.complete_activity(session, ctx, activity_id, tenant_user_id)
    return {"id": str(row.id)}


@router.get("/tenant/dashboard")
def dashboard_api(
    tenant_user_id: uuid.UUID | None = Query(default=None),
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    return service.tenant_dashboard(session, ctx, tenant_user_id)


@router.put("/leaderboard/opt-in")
def leaderboard_opt_in_api(
    body: LeaderboardBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.set_leaderboard_opt_in(session, ctx, body.opted_in, body.display_name)
    return {"opted_in": row.opted_in, "display_name": row.display_name}


@router.get("/leaderboard")
def leaderboard_api(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> list[dict[str, Any]]:
    service.assert_addon(session, get_settings(), ctx.organisation_id)
    return service.leaderboard(session, ctx)


@router.post("/ai/suggest")
def ai_api(body: AiBody, session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    return service.ai_suggest(session, ctx, body.prompt)


@router.get("/reports/dashboard")
def reports_api(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    return service.admin_reports(session, ctx)
