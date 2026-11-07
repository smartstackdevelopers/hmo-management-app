"""F2.13 organisation workflows API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.org_workflows import dashboard, decisions, forms, inbox, sharing, workflows
from app.org_workflows.schemas import (
    ApprovalDecide,
    AssignReviewer,
    CustomFormCreate,
    CustomFormUpdate,
    SharingAccessBody,
    SharingGrantCreate,
    SharingRevoke,
    SubmissionCreate,
    SubmissionReview,
    WorkflowCreate,
    WorkflowUpdate,
)
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/org-workflows", tags=["org-workflows"])


@router.get("/dashboard")
def get_dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return dashboard.dashboard(session, org)


@router.get("/approvals/inbox")
def list_approvals_inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    source_type: str | None = None,
    q: str | None = None,
    include_completed: bool = False,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    items = inbox.collect_inbox_items(
        session, org, status_filter=status, source_type=source_type, q=q, include_completed=include_completed
    )
    page_items, total = inbox.paginate(items, page, page_size)
    return {"items": page_items, "page": page, "page_size": page_size, "total": total}


@router.post("/approvals/{source_type}/{source_id}/decide")
def decide_approval(
    source_type: str,
    source_id: uuid.UUID,
    body: ApprovalDecide,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return decisions.decide_approval(session, org, source_type, source_id, body)


@router.post("/approvals/{source_type}/{source_id}/assign")
def assign_reviewer(
    source_type: str,
    source_id: uuid.UUID,
    body: AssignReviewer,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return decisions.assign_reviewer(session, org, source_type, source_id, body)


@router.get("/workflows")
def list_workflows(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": workflows.list_workflows(session, org)}


@router.post("/workflows")
def create_workflow(
    body: WorkflowCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return workflows.create_workflow(session, org, body)


@router.get("/workflows/{workflow_id}")
def get_workflow(
    workflow_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return workflows.get_workflow(session, org, workflow_id)


@router.patch("/workflows/{workflow_id}")
def patch_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return workflows.update_workflow(session, org, workflow_id, body)


@router.post("/workflows/{workflow_id}/activate")
def activate_workflow(
    workflow_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return workflows.set_workflow_status(session, org, workflow_id, active=True)


@router.post("/workflows/{workflow_id}/deactivate")
def deactivate_workflow(
    workflow_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return workflows.set_workflow_status(session, org, workflow_id, active=False)


@router.get("/workflows/{workflow_id}/versions")
def workflow_versions(
    workflow_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": workflows.list_workflow_versions(session, org, workflow_id)}


@router.get("/forms")
def list_forms(
    published_only: bool = False,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": forms.list_forms(session, org, published_only=published_only)}


@router.post("/forms")
def create_form(
    body: CustomFormCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return forms.create_form(session, org, body)


@router.patch("/forms/{form_id}")
def update_form(
    form_id: uuid.UUID,
    body: CustomFormUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return forms.update_form(session, org, form_id, body)


@router.post("/forms/{form_id}/publish")
def publish_form(
    form_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return forms.publish_form(session, org, form_id)


@router.post("/forms/{form_id}/deactivate")
def deactivate_form(
    form_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return forms.deactivate_form(session, org, form_id)


@router.get("/forms/{form_id}/versions")
def form_versions(
    form_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": forms.list_form_versions(session, org, form_id)}


@router.get("/forms/{form_id}/preview")
def preview_form(
    form_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return forms.preview_form(session, org, form_id)


@router.get("/submissions")
def list_submissions(
    own_only: bool = Query(False),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": forms.list_submissions(session, org, own_only=own_only)}


@router.post("/submissions")
def create_submission(
    body: SubmissionCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return forms.create_submission(session, org, body)


@router.get("/submissions/{submission_id}")
def get_submission(
    submission_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return forms.get_submission(session, org, submission_id)


@router.post("/submissions/{submission_id}/submit")
def submit_draft(
    submission_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return forms.submit_draft(session, org, submission_id)


@router.post("/submissions/{submission_id}/review")
def review_submission(
    submission_id: uuid.UUID,
    body: SubmissionReview,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return forms.review_submission(session, org, submission_id, body)


@router.get("/sharing")
def list_sharing(
    active_only: bool = Query(True),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": sharing.list_grants(session, org, active_only=active_only)}


@router.post("/sharing")
def create_sharing(
    body: SharingGrantCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return sharing.create_grant(session, org, body)


@router.get("/sharing/{grant_id}")
def get_sharing(
    grant_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return sharing.get_grant(session, org, grant_id)


@router.post("/sharing/{grant_id}/revoke")
def revoke_sharing(
    grant_id: uuid.UUID,
    body: SharingRevoke | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return sharing.revoke_grant(session, org, grant_id, body)


@router.post("/sharing/access")
def sharing_access(
    body: SharingAccessBody,
    request: Request,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    client_ip = request.client.host if request.client else None
    return sharing.access_by_token(session, org, body.token, client_ip=client_ip)
