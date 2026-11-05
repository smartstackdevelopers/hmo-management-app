from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models.enums import RecordStatus
from app.db.session import get_session
from app.rbac.context import AuthorizationContext
from app.rbac.deps import require_perm
from app.rbac.permissions import Permission
from app.records import room_service
from app.records.schemas import RoomCreate, RoomOut, RoomUpdate
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=RoomOut, status_code=201)
def create_room(
    body: RoomCreate,
    _authz: AuthorizationContext = Depends(require_perm(Permission.ROOMS_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return room_service.create_room(session, org, body)


@router.get("", response_model=dict[str, Any])
def list_rooms(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    property_id: uuid.UUID | None = Query(None),
    q: str | None = Query(None),
    status_filter: RecordStatus | None = Query(None, alias="status"),
    _authz: AuthorizationContext = Depends(require_perm(Permission.ROOMS_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = room_service.list_rooms(
        session,
        org,
        page=page,
        page_size=page_size,
        property_id=property_id,
        q=q,
        status_filter=status_filter,
    )
    return {
        "items": [RoomOut.model_validate(row).model_dump(mode="json") for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{room_id}", response_model=RoomOut)
def get_room(
    room_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(require_perm(Permission.ROOMS_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return room_service.get_room(session, org, room_id)


@router.patch("/{room_id}", response_model=RoomOut)
def patch_room(
    room_id: uuid.UUID,
    body: RoomUpdate,
    _authz: AuthorizationContext = Depends(require_perm(Permission.ROOMS_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return room_service.update_room(session, org, room_id, body)


@router.delete("/{room_id}", response_model=RoomOut)
def delete_room(
    room_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(require_perm(Permission.ROOMS_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    """Archive room. Hard delete is not used in F1.6."""
    return room_service.archive_room(session, org, room_id)
