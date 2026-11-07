"""F3.10 Tenant Assistant API — approved content only."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.tenant_assistant import service as ta_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/tenant-assistant", tags=["tenant-assistant"])


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=2000)
    conversation_id: UUID | None = None


@router.get("/availability")
def availability(
    org: OrganisationContext = Depends(get_organisation_context),
) -> dict:
    return ta_service.availability(org)


@router.post("/ask")
def ask(
    body: AskRequest,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    result = ta_service.ask(
        session,
        org,
        question=body.question,
        conversation_id=body.conversation_id,
    )
    session.commit()
    return result


@router.get("/conversations")
def conversations(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return ta_service.list_conversations(session, org)


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return ta_service.get_conversation(session, org, conversation_id)
