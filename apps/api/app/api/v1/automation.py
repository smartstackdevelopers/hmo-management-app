"""F6.3 automation rules API."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.automation import engine as automation_engine
from app.automation import jobs as automation_jobs
from app.automation import service as automation_service
from app.automation.access import require_rules_manage
from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/automation", tags=["automation"])


class RuleCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: Literal["reminder", "escalation", "compliance_sweep"]
    trigger_condition: str
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    action_type: Literal[
        "create_reminder", "escalate_record", "run_compliance_sweep", "create_approval_request"
    ]
    action_config: dict[str, Any] = Field(default_factory=dict)
    frequency: Literal["hourly", "daily", "weekly", "manual"] = "daily"
    is_enabled: bool = True


class RuleUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    trigger_config: dict[str, Any] | None = None
    action_config: dict[str, Any] | None = None
    frequency: Literal["hourly", "daily", "weekly", "manual"] | None = None
    is_enabled: bool | None = None


class EscalationStatusBody(BaseModel):
    status: Literal["open", "acknowledged", "resolved", "dismissed"]
    resolution_note: str | None = None


@router.get("/dashboard")
def get_dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return automation_service.dashboard(session, org)


@router.get("/rules")
def list_rules(
    category: str | None = None,
    is_enabled: bool | None = None,
    search: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {
        "items": automation_service.list_rules(
            session, org, category=category, is_enabled=is_enabled, search=search
        )
    }


@router.post("/rules")
def create_rule(
    body: RuleCreateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return automation_service.create_rule(
        session,
        org,
        name=body.name,
        description=body.description,
        category=body.category,
        trigger_condition=body.trigger_condition,
        trigger_config=body.trigger_config,
        action_type=body.action_type,
        action_config=body.action_config,
        frequency=body.frequency,
        is_enabled=body.is_enabled,
    )


@router.get("/rules/{rule_id}")
def get_rule(
    rule_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return automation_service.get_rule(session, org, rule_id)


@router.patch("/rules/{rule_id}")
def update_rule(
    rule_id: uuid.UUID,
    body: RuleUpdateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return automation_service.update_rule(
        session,
        org,
        rule_id,
        name=body.name,
        description=body.description,
        trigger_config=body.trigger_config,
        action_config=body.action_config,
        frequency=body.frequency,
        is_enabled=body.is_enabled,
    )


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return automation_service.delete_rule(session, org, rule_id)


@router.post("/rules/{rule_id}/run")
def run_rule_now(
    rule_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    require_rules_manage(org)
    rule = automation_service.get_rule(session, org, rule_id)
    result = automation_engine.execute_rule(session, uuid.UUID(rule["id"]), force=True)
    return result


@router.get("/runs")
def list_runs(
    rule_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {
        "items": automation_service.list_runs(
            session, org, rule_id=rule_id, status_filter=status, limit=limit
        )
    }


@router.post("/runs/{run_id}/retry")
def retry_run(
    run_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    require_rules_manage(org)
    # Ensure run belongs to org via list filter semantics
    runs = automation_service.list_runs(session, org, limit=500)
    if not any(r["id"] == str(run_id) for r in runs):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Run not found")
    result = automation_jobs.retry_failed_run(session, run_id)
    if not result.get("ok"):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=result.get("error", "retry_failed"))
    return result


@router.get("/escalations")
def list_escalations(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {
        "items": automation_service.list_escalations(session, org, status_filter=status, limit=limit)
    }


@router.patch("/escalations/{escalation_id}")
def patch_escalation(
    escalation_id: uuid.UUID,
    body: EscalationStatusBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return automation_service.update_escalation_status(
        session, org, escalation_id, new_status=body.status, resolution_note=body.resolution_note
    )


@router.get("/compliance-issues")
def list_compliance_issues(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {
        "items": automation_service.list_compliance_issues(
            session, org, status_filter=status, limit=limit
        )
    }
