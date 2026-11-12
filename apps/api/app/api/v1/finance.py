"""F6.6 Finance & Budgets API — ledger only; no payment gateways."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.finance import service as finance_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/finance", tags=["finance"])


class RecordCreateBody(BaseModel):
    record_type: Literal["income", "expense", "other"]
    category_code: str = Field(min_length=1, max_length=64)
    category_label: str | None = None
    amount: Decimal = Field(ge=0)
    currency: str = "GBP"
    effective_date: date
    reference: str | None = None
    description: str | None = None
    status: Literal["draft", "posted"] = "draft"
    property_id: uuid.UUID | None = None
    rent_record_id: uuid.UUID | None = None
    supporting_file_id: uuid.UUID | None = None


class RecordUpdateBody(BaseModel):
    category_code: str | None = None
    category_label: str | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    effective_date: date | None = None
    reference: str | None = None
    description: str | None = None
    status: Literal["draft", "posted"] | None = None
    property_id: uuid.UUID | None = None
    supporting_file_id: uuid.UUID | None = None
    clear_supporting_file: bool = False


class VoidBody(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class BudgetLineBody(BaseModel):
    category_code: str
    category_label: str | None = None
    planned_amount: Decimal = Field(ge=0)
    sort_order: int = 0
    notes: str | None = None


class BudgetCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    period_start: date
    period_end: date
    currency: str = "GBP"
    notes: str | None = None
    property_id: uuid.UUID | None = None
    status: Literal["draft", "active", "closed"] = "draft"
    lines: list[BudgetLineBody] = Field(default_factory=list)


class BudgetStatusBody(BaseModel):
    status: Literal["draft", "active", "closed"]


@router.get("/dashboard")
def dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return finance_service.dashboard(session, org)


@router.get("/categories")
def list_categories(
    org: OrganisationContext = Depends(get_organisation_context),
) -> dict:
    from app.finance.access import require_finance_read

    require_finance_read(org)
    return {"items": finance_service.categories()}


@router.get("/records")
def list_records(
    record_type: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {
        "items": finance_service.list_records(
            session, org, record_type=record_type, status=status, limit=limit
        )
    }


@router.post("/records")
def create_record(
    body: RecordCreateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return finance_service.create_record(session, org, **body.model_dump())


@router.patch("/records/{record_id}")
def update_record(
    record_id: uuid.UUID,
    body: RecordUpdateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return finance_service.update_record(
        session, org, record_id, **body.model_dump(exclude_unset=True)
    )


@router.post("/records/{record_id}/void")
def void_record(
    record_id: uuid.UUID,
    body: VoidBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return finance_service.void_record(session, org, record_id, body.reason)


@router.get("/budgets")
def list_budgets(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": finance_service.list_budgets(session, org)}


@router.post("/budgets")
def create_budget(
    body: BudgetCreateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    payload = body.model_dump()
    lines = payload.pop("lines")
    return finance_service.create_budget(session, org, lines=lines, **payload)


@router.patch("/budgets/{budget_id}/status")
def patch_budget_status(
    budget_id: uuid.UUID,
    body: BudgetStatusBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return finance_service.update_budget_status(session, org, budget_id, body.status)


@router.get("/budgets/{budget_id}/variance")
def budget_variance(
    budget_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return finance_service.budget_variance(session, org, budget_id)


@router.get("/exports/records")
def export_records(
    export_format: Literal["csv", "pdf", "xlsx"] = "csv",
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    content, media_type, filename = finance_service.export_records(
        session, org, export_format=export_format
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
