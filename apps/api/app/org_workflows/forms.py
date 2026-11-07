"""Organisation custom forms and submissions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.org_workflows import (
    OrganisationApprovalWorkflow,
    OrganisationApprovalWorkflowVersion,
    OrganisationCustomForm,
    OrganisationCustomFormSubmission,
    OrganisationCustomFormVersion,
)
from app.org_workflows import form_schema
from app.org_workflows.access import (
    require_forms_manage,
    require_forms_publish,
    require_forms_submit,
    require_submissions_read,
    require_submissions_review,
)
from app.org_workflows.schemas import CustomFormCreate, CustomFormUpdate, SubmissionCreate, SubmissionReview
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _next_sub_ref(session: Session, org_id: uuid.UUID) -> str:
    count = session.scalar(
        select(func.count()).select_from(OrganisationCustomFormSubmission).where(
            OrganisationCustomFormSubmission.organisation_id == org_id
        )
    ) or 0
    return f"FORM-SUB-{count + 1:06d}"


def _audit(session: Session, ctx: OrganisationContext, action: str, rtype: str, rid: uuid.UUID, summary: str) -> None:
    record_event(
        session,
        action=action,
        resource_type=rtype,
        resource_id=str(rid),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=summary,
        raise_on_error=False,
    )


def create_form(session: Session, ctx: OrganisationContext, body: CustomFormCreate) -> dict[str, Any]:
    require_forms_manage(ctx)
    schema = form_schema.validate_form_schema(body.form_schema)
    clash = session.scalar(
        select(OrganisationCustomForm.id).where(
            OrganisationCustomForm.organisation_id == ctx.organisation_id,
            OrganisationCustomForm.code == body.code,
        )
    )
    if clash:
        raise HTTPException(status_code=409, detail="Form code already exists")
    if body.workflow_id:
        wf = session.get(OrganisationApprovalWorkflow, body.workflow_id)
        if wf is None or wf.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=400, detail="Invalid workflow")
    form = OrganisationCustomForm(
        organisation_id=ctx.organisation_id,
        code=body.code.strip(),
        title=body.title.strip(),
        description=body.description,
        status="draft",
        workflow_id=body.workflow_id,
    )
    session.add(form)
    session.flush()
    version = OrganisationCustomFormVersion(
        organisation_id=ctx.organisation_id,
        form_id=form.id,
        version_number=1,
        schema_json=schema,
    )
    session.add(version)
    _audit(session, ctx, audit_events.ORG_FORM_CREATE, "org_custom_form", form.id, "Custom form created")
    session.flush()
    return {
        "id": str(form.id),
        "code": form.code,
        "title": form.title,
        "status": form.status,
        "draft_version_id": str(version.id),
    }


def list_forms(session: Session, ctx: OrganisationContext, *, published_only: bool = False) -> list[dict[str, Any]]:
    if published_only:
        require_forms_submit(ctx)
    else:
        require_forms_manage(ctx)
    stmt = select(OrganisationCustomForm).where(OrganisationCustomForm.organisation_id == ctx.organisation_id)
    if published_only:
        stmt = stmt.where(OrganisationCustomForm.status == "published")
    rows = session.scalars(stmt.order_by(OrganisationCustomForm.title.asc())).all()
    return [
        {
            "id": str(r.id),
            "code": r.code,
            "title": r.title,
            "description": r.description,
            "status": r.status,
            "published_version_id": str(r.published_version_id) if r.published_version_id else None,
        }
        for r in rows
    ]


def update_form(
    session: Session, ctx: OrganisationContext, form_id: uuid.UUID, body: CustomFormUpdate
) -> dict[str, Any]:
    require_forms_manage(ctx)
    form = session.get(OrganisationCustomForm, form_id)
    if form is None or form.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Form not found")
    if form.status == "published" and body.form_schema is not None:
        raise HTTPException(status_code=409, detail="Published forms require a new version via publish")
    if body.title is not None:
        form.title = body.title.strip()
    if body.description is not None:
        form.description = body.description
    if body.workflow_id is not None:
        form.workflow_id = body.workflow_id
    if body.form_schema is not None:
        schema = form_schema.validate_form_schema(body.form_schema)
        max_ver = session.scalar(
            select(func.max(OrganisationCustomFormVersion.version_number)).where(
                OrganisationCustomFormVersion.form_id == form.id
            )
        ) or 0
        session.add(
            OrganisationCustomFormVersion(
                organisation_id=ctx.organisation_id,
                form_id=form.id,
                version_number=max_ver + 1,
                schema_json=schema,
            )
        )
    session.flush()
    return {"id": str(form.id), "status": form.status}


def publish_form(session: Session, ctx: OrganisationContext, form_id: uuid.UUID) -> dict[str, Any]:
    require_forms_publish(ctx)
    form = session.get(OrganisationCustomForm, form_id)
    if form is None or form.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Form not found")
    latest = session.scalar(
        select(OrganisationCustomFormVersion)
        .where(OrganisationCustomFormVersion.form_id == form.id)
        .order_by(OrganisationCustomFormVersion.version_number.desc())
        .limit(1)
    )
    if latest is None:
        raise HTTPException(status_code=400, detail="No form version to publish")
    latest.published_at = _now()
    latest.published_by_user_id = ctx.user_id
    form.published_version_id = latest.id
    form.status = "published"
    _audit(session, ctx, audit_events.ORG_FORM_PUBLISH, "org_custom_form", form.id, "Form published")
    session.flush()
    return {"id": str(form.id), "published_version_id": str(latest.id), "status": form.status}


def deactivate_form(session: Session, ctx: OrganisationContext, form_id: uuid.UUID) -> dict[str, Any]:
    require_forms_manage(ctx)
    form = session.get(OrganisationCustomForm, form_id)
    if form is None or form.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Form not found")
    form.status = "inactive"
    session.flush()
    return {"id": str(form.id), "status": form.status}


def list_form_versions(session: Session, ctx: OrganisationContext, form_id: uuid.UUID) -> list[dict[str, Any]]:
    require_forms_manage(ctx)
    form = session.get(OrganisationCustomForm, form_id)
    if form is None or form.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Form not found")
    rows = session.scalars(
        select(OrganisationCustomFormVersion)
        .where(OrganisationCustomFormVersion.form_id == form_id)
        .order_by(OrganisationCustomFormVersion.version_number.desc())
    ).all()
    return [
        {
            "id": str(v.id),
            "version_number": v.version_number,
            "schema": v.schema_json,
            "published_at": v.published_at.isoformat() if v.published_at else None,
        }
        for v in rows
    ]


def preview_form(session: Session, ctx: OrganisationContext, form_id: uuid.UUID) -> dict[str, Any]:
    require_forms_manage(ctx)
    form = session.get(OrganisationCustomForm, form_id)
    if form is None or form.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Form not found")
    vid = form.published_version_id
    if not vid:
        latest = session.scalar(
            select(OrganisationCustomFormVersion)
            .where(OrganisationCustomFormVersion.form_id == form.id)
            .order_by(OrganisationCustomFormVersion.version_number.desc())
            .limit(1)
        )
        if latest is None:
            raise HTTPException(status_code=400, detail="No form schema")
        schema = latest.schema_json
    else:
        ver = session.get(OrganisationCustomFormVersion, vid)
        schema = ver.schema_json if ver else {}
    return {"title": form.title, "description": form.description, "schema": schema}


def create_submission(session: Session, ctx: OrganisationContext, body: SubmissionCreate) -> dict[str, Any]:
    require_forms_submit(ctx)
    form = session.get(OrganisationCustomForm, body.form_id)
    if form is None or form.organisation_id != ctx.organisation_id or form.status != "published":
        raise HTTPException(status_code=404, detail="Form not available")
    if not form.published_version_id:
        raise HTTPException(status_code=400, detail="Form not published")
    ver = session.get(OrganisationCustomFormVersion, form.published_version_id)
    if ver is None:
        raise HTTPException(status_code=500, detail="Published version missing")
    answers = form_schema.validate_answers(ver.schema_json, body.answers)
    wf_version_id = None
    if form.workflow_id:
        wf = session.get(OrganisationApprovalWorkflow, form.workflow_id)
        if wf and wf.active_version_id:
            wf_version_id = wf.active_version_id
    sub = OrganisationCustomFormSubmission(
        organisation_id=ctx.organisation_id,
        form_id=form.id,
        form_version_id=ver.id,
        workflow_version_id=wf_version_id,
        reference_number=_next_sub_ref(session, ctx.organisation_id),
        submitter_user_id=ctx.user_id,
        tenant_id=body.tenant_id,
        answers_json=answers,
        status="draft" if body.save_as_draft else "pending",
        submitted_at=None if body.save_as_draft else _now(),
    )
    session.add(sub)
    _audit(session, ctx, audit_events.ORG_FORM_SUBMISSION_CREATE, "org_custom_form_submission", sub.id, sub.status)
    session.flush()
    return {"id": str(sub.id), "reference_number": sub.reference_number, "status": sub.status}


def submit_draft(session: Session, ctx: OrganisationContext, submission_id: uuid.UUID) -> dict[str, Any]:
    require_forms_submit(ctx)
    sub = session.get(OrganisationCustomFormSubmission, submission_id)
    if sub is None or sub.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Not found")
    if sub.submitter_user_id != ctx.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if sub.status != "draft":
        raise HTTPException(status_code=409, detail="Not a draft")
    sub.status = "pending"
    sub.submitted_at = _now()
    session.flush()
    return {"id": str(sub.id), "status": sub.status}


def list_submissions(session: Session, ctx: OrganisationContext, *, own_only: bool) -> list[dict[str, Any]]:
    require_submissions_read(ctx)
    stmt = select(OrganisationCustomFormSubmission).where(
        OrganisationCustomFormSubmission.organisation_id == ctx.organisation_id
    )
    if own_only:
        stmt = stmt.where(OrganisationCustomFormSubmission.submitter_user_id == ctx.user_id)
    rows = session.scalars(stmt.order_by(OrganisationCustomFormSubmission.created_at.desc())).all()
    return [
        {
            "id": str(r.id),
            "reference_number": r.reference_number,
            "form_id": str(r.form_id),
            "status": r.status,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        }
        for r in rows
    ]


def get_submission(session: Session, ctx: OrganisationContext, submission_id: uuid.UUID) -> dict[str, Any]:
    require_submissions_read(ctx)
    sub = session.get(OrganisationCustomFormSubmission, submission_id)
    if sub is None or sub.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Not found")
    if not ctx.authorization.has_permission(Permission.ORGANISATION_FORMS_SUBMISSIONS_REVIEW) and sub.submitter_user_id != ctx.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "id": str(sub.id),
        "reference_number": sub.reference_number,
        "form_id": str(sub.form_id),
        "form_version_id": str(sub.form_version_id),
        "answers": sub.answers_json,
        "status": sub.status,
        "decision_notes": sub.decision_notes,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
    }


def review_submission(
    session: Session, ctx: OrganisationContext, submission_id: uuid.UUID, body: SubmissionReview
) -> dict[str, Any]:
    require_submissions_review(ctx)
    from app.org_workflows.decisions import decide_approval
    from app.org_workflows.schemas import ApprovalDecide

    return decide_approval(
        session,
        ctx,
        "custom_form_submission",
        submission_id,
        ApprovalDecide(action=body.action, reason=body.reason),
    )
