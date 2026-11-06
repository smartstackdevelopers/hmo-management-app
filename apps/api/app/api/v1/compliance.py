"""F2.3 training and safeguarding reminder APIs."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.compliance import service as compliance_service
from app.compliance.schemas import (
    SafeguardingCreate,
    SafeguardingOut,
    SafeguardingUpdate,
    TrainingCreate,
    TrainingOut,
    TrainingUpdate,
)
from app.db.session import get_session
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter()
training_router = APIRouter(prefix="/training", tags=["staff-training"])
safeguarding_router = APIRouter(
    prefix="/safeguarding-reminders", tags=["safeguarding-reminders"]
)


def _page(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@training_router.post("", response_model=TrainingOut, status_code=201)
def create_training(
    body: TrainingCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return compliance_service.training_out_dict(
        compliance_service.create_training(session, org, body)
    )


@training_router.get("", response_model=dict[str, Any])
def list_training(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    staff_user_id: uuid.UUID | None = Query(None),
    category: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    expiring_only: bool = Query(False),
    expired_only: bool = Query(False),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = compliance_service.list_training(
        session,
        org,
        page=page,
        page_size=page_size,
        staff_user_id=staff_user_id,
        category=category,
        status_filter=status_filter,
        expiring_only=expiring_only,
        expired_only=expired_only,
    )
    return _page(
        [compliance_service.training_out_dict(row) for row in rows],
        page,
        page_size,
        total,
    )


@training_router.get("/{training_id}", response_model=TrainingOut)
def get_training(
    training_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return compliance_service.training_out_dict(
        compliance_service.get_training(session, org, training_id)
    )


@training_router.patch("/{training_id}", response_model=TrainingOut)
def patch_training(
    training_id: uuid.UUID,
    body: TrainingUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return compliance_service.training_out_dict(
        compliance_service.update_training(session, org, training_id, body)
    )


@safeguarding_router.post("", response_model=SafeguardingOut, status_code=201)
def create_safeguarding(
    body: SafeguardingCreate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return compliance_service.create_safeguarding(session, org, body)


@safeguarding_router.get("", response_model=dict[str, Any])
def list_safeguarding(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    overdue_only: bool = Query(False),
    assigned_user_id: uuid.UUID | None = Query(None),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = compliance_service.list_safeguarding(
        session,
        org,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        overdue_only=overdue_only,
        assigned_user_id=assigned_user_id,
    )
    return _page(
        [SafeguardingOut.model_validate(row).model_dump(mode="json") for row in rows],
        page,
        page_size,
        total,
    )


@safeguarding_router.get("/{reminder_id}", response_model=SafeguardingOut)
def get_safeguarding(
    reminder_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return compliance_service.get_safeguarding(session, org, reminder_id)


@safeguarding_router.patch("/{reminder_id}", response_model=SafeguardingOut)
def patch_safeguarding(
    reminder_id: uuid.UUID,
    body: SafeguardingUpdate,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return compliance_service.update_safeguarding(session, org, reminder_id, body)


@safeguarding_router.post("/{reminder_id}/acknowledge", response_model=SafeguardingOut)
def acknowledge_safeguarding(
    reminder_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return compliance_service.acknowledge_safeguarding(session, org, reminder_id)


@safeguarding_router.post("/{reminder_id}/complete", response_model=SafeguardingOut)
def complete_safeguarding(
    reminder_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return compliance_service.complete_safeguarding(session, org, reminder_id)


@safeguarding_router.post("/{reminder_id}/cancel", response_model=SafeguardingOut)
def cancel_safeguarding(
    reminder_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return compliance_service.cancel_safeguarding(session, org, reminder_id)


router.include_router(training_router)
router.include_router(safeguarding_router)
