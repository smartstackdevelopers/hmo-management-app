"""F3.6 document checker API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.document_checks import service as check_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/document-checks", tags=["document-checks"])


class RunDocumentCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    force: bool = False


class FindingDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(confirm|dismiss)$")
    review_comment: str | None = Field(default=None, max_length=2000)


class ReviewCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_comment: str | None = Field(default=None, max_length=2000)


class RuleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_code: str = ""
    rule_kind: str
    parameter: str = ""
    enabled: bool = True


@router.post("")
def run_check(
    body: RunDocumentCheckRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = check_service.run_check(session, org, document_id=body.document_id, force=body.force)
    session.commit()
    return result


@router.get("/documents/{document_id}")
def list_for_document(
    document_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return check_service.list_checks(session, org, document_id)


@router.post("/rules")
def save_rule(
    body: RuleRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = check_service.save_rule(
        session,
        org,
        category_code=body.category_code,
        rule_kind=body.rule_kind,
        parameter=body.parameter,
        enabled=body.enabled,
    )
    session.commit()
    return result


@router.get("/{check_id}")
def get_one(
    check_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return check_service.get_check(session, org, check_id)


@router.get("/{check_id}/text")
def get_text(
    check_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return check_service.get_text(session, org, check_id)


@router.post("/{check_id}/review")
def review(
    check_id: UUID,
    body: ReviewCheckRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = check_service.review_check(session, org, check_id, review_comment=body.review_comment)
    session.commit()
    return result


@router.post("/findings/{finding_id}/decide")
def decide(
    finding_id: UUID,
    body: FindingDecisionRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = check_service.decide_finding(
        session,
        org,
        finding_id,
        decision=body.decision,
        review_comment=body.review_comment,
    )
    session.commit()
    return result
