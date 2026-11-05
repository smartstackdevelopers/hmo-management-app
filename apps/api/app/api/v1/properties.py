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
from app.records import property_service
from app.records.schemas import PropertyCreate, PropertyOut, PropertyUpdate
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("", response_model=PropertyOut, status_code=201)
def create_property(
    body: PropertyCreate,
    _authz: AuthorizationContext = Depends(require_perm(Permission.PROPERTIES_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return property_service.create_property(session, org, body)


@router.get("", response_model=dict[str, Any])
def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    status_filter: RecordStatus | None = Query(None, alias="status"),
    _authz: AuthorizationContext = Depends(require_perm(Permission.PROPERTIES_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = property_service.list_properties(
        session, org, page=page, page_size=page_size, q=q, status_filter=status_filter
    )
    return {
        "items": [PropertyOut.model_validate(row).model_dump(mode="json") for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(
    property_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(require_perm(Permission.PROPERTIES_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return property_service.get_property(session, org, property_id)


@router.patch("/{property_id}", response_model=PropertyOut)
def patch_property(
    property_id: uuid.UUID,
    body: PropertyUpdate,
    _authz: AuthorizationContext = Depends(require_perm(Permission.PROPERTIES_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return property_service.update_property(session, org, property_id, body)


@router.delete("/{property_id}", response_model=PropertyOut)
def delete_property(
    property_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(require_perm(Permission.PROPERTIES_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    """Archive property. Dependent rooms remain; hard delete is blocked by design."""
    return property_service.archive_property(session, org, property_id)
