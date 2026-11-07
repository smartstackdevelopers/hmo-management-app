"""F3.9 Compliance Agent API. Rules identify gaps; AI explains; humans decide."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.compliance_agent import service as compliance_service
from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/compliance-agent", tags=["compliance-agent"])


class SweepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modules: list[str] | None = None


class FindingReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(confirm|dismiss|investigate)$")
    review_comment: str | None = Field(default=None, max_length=2000)
    corrective_action_ref: str | None = Field(default=None, max_length=255)


class FindingResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_comment: str | None = Field(default=None, max_length=2000)
    corrective_action_ref: str | None = Field(default=None, max_length=255)


@router.get("/rules")
def rules_catalog(
    org: OrganisationContext = Depends(get_organisation_context),
) -> dict:
    return compliance_service.list_rules_catalog(org)


@router.post("/sweeps")
def start_sweep(
    body: SweepRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = compliance_service.run_sweep(session, org, modules=body.modules, trigger="manual")
    session.commit()
    return result


@router.get("/sweeps")
def sweeps(
    limit: int = Query(20, ge=1, le=100),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return compliance_service.list_sweeps(session, org, limit=limit)


@router.get("/sweeps/{sweep_id}")
def get_sweep(
    sweep_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return compliance_service.get_sweep(session, org, sweep_id)


@router.get("/findings")
def findings(
    module: str | None = None,
    review_status: str | None = None,
    resolution_status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return compliance_service.list_findings(
        session,
        org,
        module=module,
        review_status=review_status,
        resolution_status=resolution_status,
        limit=limit,
    )


@router.get("/findings/{finding_id}")
def get_finding(
    finding_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return compliance_service.get_finding(session, org, finding_id)


@router.post("/findings/{finding_id}/review")
def review_finding(
    finding_id: UUID,
    body: FindingReviewRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = compliance_service.review_finding(
        session,
        org,
        finding_id,
        decision=body.decision,
        review_comment=body.review_comment,
        corrective_action_ref=body.corrective_action_ref,
    )
    session.commit()
    return result


@router.post("/findings/{finding_id}/resolve")
def resolve_finding(
    finding_id: UUID,
    body: FindingResolveRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = compliance_service.resolve_finding(
        session,
        org,
        finding_id,
        review_comment=body.review_comment,
        corrective_action_ref=body.corrective_action_ref,
    )
    session.commit()
    return result
