"""F4.3 device push token API. Tokens are bound to the authenticated user and organisation."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.push.schemas import PushDeviceRegister
from app.push import service as push_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/push", tags=["push"])


@router.post("/devices", status_code=status.HTTP_201_CREATED)
def register_device(
    body: PushDeviceRegister,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return push_service.register_device(session, org, body)


@router.get("/devices")
def list_devices(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": push_service.list_own_devices(session, org)}


@router.post("/devices/{device_id}/deactivate")
def deactivate_device(
    device_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return push_service.deactivate_device(session, org, device_id)


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Response:
    push_service.deactivate_device(session, org, device_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
