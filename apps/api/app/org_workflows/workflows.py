"""Approval workflow configuration (versioned, not a BPM engine)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.org_workflows import OrganisationApprovalWorkflow, OrganisationApprovalWorkflowVersion
from app.org_workflows.access import require_workflow_manage
from app.org_workflows.schemas import WorkflowCreate, WorkflowUpdate
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(session: Session, ctx: OrganisationContext, action: str, rid: uuid.UUID, summary: str) -> None:
    record_event(
        session,
        action=action,
        resource_type="org_approval_workflow",
        resource_id=str(rid),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=summary,
        raise_on_error=False,
    )


def _serialize_workflow(row: OrganisationApprovalWorkflow) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "code": row.code,
        "name": row.name,
        "description": row.description,
        "process_type": row.process_type,
        "status": row.status,
        "active_version_id": str(row.active_version_id) if row.active_version_id else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def create_workflow(session: Session, ctx: OrganisationContext, body: WorkflowCreate) -> dict[str, Any]:
    require_workflow_manage(ctx)
    clash = session.scalar(
        select(OrganisationApprovalWorkflow.id).where(
            OrganisationApprovalWorkflow.organisation_id == ctx.organisation_id,
            OrganisationApprovalWorkflow.code == body.code,
        )
    )
    if clash:
        raise HTTPException(status_code=409, detail="Workflow code already exists")
    wf = OrganisationApprovalWorkflow(
        organisation_id=ctx.organisation_id,
        code=body.code.strip(),
        name=body.name.strip(),
        description=body.description,
        process_type=body.process_type.strip(),
        status="draft",
    )
    session.add(wf)
    session.flush()
    version = OrganisationApprovalWorkflowVersion(
        organisation_id=ctx.organisation_id,
        workflow_id=wf.id,
        version_number=1,
        steps_json=[s.model_dump() for s in body.steps],
        reviewer_roles_json=body.reviewer_roles,
        created_by_user_id=ctx.user_id,
        change_notes="Initial version",
    )
    session.add(version)
    session.flush()
    wf.active_version_id = version.id
    _audit(session, ctx, audit_events.ORG_WORKFLOW_CREATE, wf.id, "Workflow created")
    session.flush()
    return _serialize_workflow(wf)


def list_workflows(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_workflow_manage(ctx)
    rows = session.scalars(
        select(OrganisationApprovalWorkflow)
        .where(OrganisationApprovalWorkflow.organisation_id == ctx.organisation_id)
        .order_by(OrganisationApprovalWorkflow.name.asc())
    ).all()
    return [_serialize_workflow(r) for r in rows]


def get_workflow(session: Session, ctx: OrganisationContext, workflow_id: uuid.UUID) -> dict[str, Any]:
    require_workflow_manage(ctx)
    row = session.get(OrganisationApprovalWorkflow, workflow_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _serialize_workflow(row)


def update_workflow(
    session: Session, ctx: OrganisationContext, workflow_id: uuid.UUID, body: WorkflowUpdate
) -> dict[str, Any]:
    require_workflow_manage(ctx)
    row = session.get(OrganisationApprovalWorkflow, workflow_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if body.name is not None:
        row.name = body.name.strip()
    if body.description is not None:
        row.description = body.description
    if body.steps is not None or body.reviewer_roles is not None:
        max_ver = session.scalar(
            select(func.max(OrganisationApprovalWorkflowVersion.version_number)).where(
                OrganisationApprovalWorkflowVersion.workflow_id == row.id
            )
        ) or 0
        prev = None
        if row.active_version_id:
            prev = session.get(OrganisationApprovalWorkflowVersion, row.active_version_id)
        version = OrganisationApprovalWorkflowVersion(
            organisation_id=ctx.organisation_id,
            workflow_id=row.id,
            version_number=max_ver + 1,
            steps_json=[s.model_dump() for s in body.steps] if body.steps is not None else (prev.steps_json if prev else []),
            reviewer_roles_json=body.reviewer_roles
            if body.reviewer_roles is not None
            else (prev.reviewer_roles_json if prev else []),
            created_by_user_id=ctx.user_id,
            change_notes=body.change_notes,
        )
        session.add(version)
        session.flush()
        row.active_version_id = version.id
    _audit(session, ctx, audit_events.ORG_WORKFLOW_UPDATE, row.id, "Workflow updated")
    session.flush()
    return _serialize_workflow(row)


def set_workflow_status(
    session: Session, ctx: OrganisationContext, workflow_id: uuid.UUID, *, active: bool
) -> dict[str, Any]:
    require_workflow_manage(ctx)
    row = session.get(OrganisationApprovalWorkflow, workflow_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if active:
        if not row.active_version_id:
            raise HTTPException(status_code=400, detail="Workflow has no version to activate")
        row.status = "active"
        action = audit_events.ORG_WORKFLOW_ACTIVATE
    else:
        row.status = "inactive"
        action = audit_events.ORG_WORKFLOW_DEACTIVATE
    _audit(session, ctx, action, row.id, f"Workflow {row.status}")
    session.flush()
    return _serialize_workflow(row)


def list_workflow_versions(session: Session, ctx: OrganisationContext, workflow_id: uuid.UUID) -> list[dict[str, Any]]:
    require_workflow_manage(ctx)
    wf = session.get(OrganisationApprovalWorkflow, workflow_id)
    if wf is None or wf.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    rows = session.scalars(
        select(OrganisationApprovalWorkflowVersion)
        .where(OrganisationApprovalWorkflowVersion.workflow_id == workflow_id)
        .order_by(OrganisationApprovalWorkflowVersion.version_number.desc())
    ).all()
    return [
        {
            "id": str(v.id),
            "version_number": v.version_number,
            "steps": v.steps_json,
            "reviewer_roles": v.reviewer_roles_json,
            "change_notes": v.change_notes,
            "created_by_user_id": str(v.created_by_user_id) if v.created_by_user_id else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in rows
    ]
