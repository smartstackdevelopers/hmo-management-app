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
from app.records import tenant_service
from app.records.schemas import TenantCreate, TenantOut, TenantUpdate
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantOut, status_code=201)
def create_tenant(
    body: TenantCreate,
    _authz: AuthorizationContext = Depends(require_perm(Permission.TENANTS_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return tenant_service.create_tenant(session, org, body)


@router.get("", response_model=dict[str, Any])
def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    status_filter: RecordStatus | None = Query(None, alias="status"),
    _authz: AuthorizationContext = Depends(require_perm(Permission.TENANTS_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rows, total = tenant_service.list_tenants(
        session, org, page=page, page_size=page_size, q=q, status_filter=status_filter
    )
    return {
        "items": [TenantOut.model_validate(row).model_dump(mode="json") for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(
    tenant_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(require_perm(Permission.TENANTS_READ)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return tenant_service.get_tenant(session, org, tenant_id)


@router.patch("/{tenant_id}", response_model=TenantOut)
def patch_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    _authz: AuthorizationContext = Depends(require_perm(Permission.TENANTS_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    return tenant_service.update_tenant(session, org, tenant_id, body)


@router.delete("/{tenant_id}", response_model=TenantOut)
def delete_tenant(
    tenant_id: uuid.UUID,
    _authz: AuthorizationContext = Depends(require_perm(Permission.TENANTS_MANAGE)),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> Any:
    """Archive tenant (safe deactivation). Hard delete is not used."""
    return tenant_service.archive_tenant(session, org, tenant_id)
