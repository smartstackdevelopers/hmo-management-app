"""F8.11 advanced automation & intelligent workflows API."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.advanced_automation import service
from app.advanced_automation.service import _settings
from app.db.session import get_session
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/advanced-automation", tags=["advanced-automation"])


class SettingsBody(BaseModel):
    enabled: bool | None = None
    ai_assistant_enabled: bool | None = None
    privacy_review_complete: bool | None = None
    notification_prefs: dict[str, Any] | None = None


class WorkflowCreateBody(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    template_key: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    triggers: list[Any] = Field(default_factory=list)
    conditions: dict[str, Any] = Field(default_factory=dict)


class WorkflowDraftBody(BaseModel):
    steps: list[dict[str, Any]] | None = None
    triggers: list[Any] | None = None
    conditions: dict[str, Any] | None = None
    change_notes: str | None = None
    create_new_version: bool = False


class TestRunBody(BaseModel):
    trigger_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalBody(BaseModel):
    approved: bool
    comment: str | None = None


class AiBody(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)


class ScheduleBody(BaseModel):
    schedule_spec: dict[str, Any] = Field(default_factory=dict)
    timezone: str = "UTC"


@router.get("/settings")
def get_settings_api(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.ADVANCED_AUTOMATION_READ)
    return service.settings_dict(_settings(session, ctx.organisation_id))


@router.patch("/settings")
def patch_settings_api(
    body: SettingsBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.update_settings(session, ctx, body.model_dump(exclude_unset=True))
    return service.settings_dict(row)


@router.get("/dashboard")
def dashboard_api(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    return service.deep_dashboard(session, ctx)


@router.get("/templates")
def templates_api(ctx: OrganisationContext = Depends(get_organisation_context)) -> list[dict[str, Any]]:
    return service.list_templates(ctx)


@router.get("/triggers")
def triggers_api(ctx: OrganisationContext = Depends(get_organisation_context)) -> list[dict[str, str]]:
    return service.list_triggers(ctx)


@router.get("/workflows")
def list_workflows_api(
    status: str | None = Query(default=None),
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> list[dict[str, Any]]:
    return service.list_workflows(session, ctx, status)


@router.post("/workflows")
def create_workflow_api(
    body: WorkflowCreateBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.create_workflow(session, ctx, body.model_dump())
    return {"id": str(row.id), "slug": row.slug, "status": row.status}


@router.put("/workflows/{workflow_id}/draft")
def save_draft_api(
    workflow_id: uuid.UUID,
    body: WorkflowDraftBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    version = service.save_draft_version(session, ctx, workflow_id, body.model_dump(exclude_unset=True))
    return {"version_id": str(version.id), "version_number": version.version_number}


@router.post("/workflows/{workflow_id}/publish")
def publish_api(
    workflow_id: uuid.UUID,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.publish_workflow(session, ctx, workflow_id)
    return {"id": str(row.id), "status": row.status}


@router.post("/workflows/{workflow_id}/test-run")
def test_run_api(
    workflow_id: uuid.UUID,
    body: TestRunBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    ex = service.run_test_execution(session, ctx, workflow_id, body.trigger_type, body.payload)
    return {"execution_id": str(ex.id), "status": ex.status, "dry_run": ex.dry_run}


@router.get("/executions")
def executions_api(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    return service.list_executions(session, ctx, limit)


@router.get("/approvals/pending")
def pending_approvals_api(
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> list[dict[str, Any]]:
    return service.list_pending_approvals(session, ctx)


@router.post("/approvals/{approval_id}/decide")
def decide_approval_api(
    approval_id: uuid.UUID,
    body: ApprovalBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.decide_approval(session, ctx, approval_id, approved=body.approved, comment=body.comment)
    return {"id": str(row.id), "status": row.status}


@router.post("/ai/suggest")
def ai_suggest_api(
    body: AiBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    return service.ai_suggest(session, ctx, body.prompt)


@router.post("/workflows/{workflow_id}/schedule")
def schedule_api(
    workflow_id: uuid.UUID,
    body: ScheduleBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.schedule_workflow(session, ctx, workflow_id, body.schedule_spec, body.timezone)
    return {"id": str(row.id), "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None}
