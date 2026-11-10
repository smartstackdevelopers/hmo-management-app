"""F4.6 device session API. Identity stays with Auth0. This registry only tracks installations."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.device_sessions.schemas import DeviceSessionRegister, DeviceSessionRevoke
from app.device_sessions import service as device_session_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context, get_organisation_context_allow_inactive_device

router = APIRouter(prefix="/device-sessions", tags=["device-sessions"])


@router.post("", status_code=status.HTTP_201_CREATED)
def register_device_session(
    body: DeviceSessionRegister,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return device_session_service.register_session(session, org, body)


@router.get("/current")
def current_device_session(
    x_device_session_id: Annotated[str | None, Header(alias="X-Device-Session-Id")] = None,
    org: OrganisationContext = Depends(get_organisation_context_allow_inactive_device),
    session: Session = Depends(get_session),
) -> dict:
    return device_session_service.get_current_session(session, org, x_device_session_id)


@router.get("")
def list_device_sessions(
    x_device_session_id: Annotated[str | None, Header(alias="X-Device-Session-Id")] = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": device_session_service.list_own_sessions(session, org, x_device_session_id)}


@router.get("/{session_id}")
def get_device_session(
    session_id: uuid.UUID,
    x_device_session_id: Annotated[str | None, Header(alias="X-Device-Session-Id")] = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return device_session_service.get_session(session, org, session_id, x_device_session_id)


@router.post("/{session_id}/revoke")
def revoke_device_session(
    session_id: uuid.UUID,
    body: DeviceSessionRevoke | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    reason = body.revocation_reason if body else None
    return device_session_service.revoke_session(session, org, session_id, reason)


@router.post("/{session_id}/report-lost")
def report_device_session_lost(
    session_id: uuid.UUID,
    body: DeviceSessionRevoke | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    reason = body.revocation_reason if body else None
    return device_session_service.report_lost(session, org, session_id, reason)
