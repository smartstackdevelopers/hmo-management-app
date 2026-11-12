"""F6.4 Integration Hub API."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.integrations import service as integration_service
from app.integrations import sync as integration_sync
from app.integrations.access import require_integrations_read
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    provider_key: str
    description: str | None = None
    api_base_url: str | None = None
    auth_type: Literal["api_key", "bearer", "oauth2", "none"] = "api_key"
    config: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class IntegrationUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    api_base_url: str | None = None
    auth_type: Literal["api_key", "bearer", "oauth2", "none"] | None = None
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    is_enabled: bool | None = None


class MappingCreateBody(BaseModel):
    name: str = "default"
    mappings: list[dict[str, Any]] = Field(default_factory=list)


class SyncStartBody(BaseModel):
    direction: Literal["import", "export", "bidirectional", "health_check"] = "health_check"
    idempotency_key: str | None = None


@router.get("/dashboard")
def dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    """Integration hub overview metrics from live database records."""
    return integration_service.dashboard(session, org)


@router.get("/providers")
def list_providers(
    org: OrganisationContext = Depends(get_organisation_context),
) -> dict:
    """Catalog of foundation provider adapters (not live partner status)."""
    require_integrations_read(org)
    return {"items": integration_service.provider_catalog()}


@router.get("/sync-jobs")
def list_sync_jobs(
    integration_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {
        "items": integration_service.list_sync_jobs(
            session, org, integration_id=integration_id, status=status, limit=limit
        )
    }


@router.post("/sync-jobs/{job_id}/cancel")
def cancel_sync_job(
    job_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return integration_sync.request_cancel(session, org, job_id)


@router.get("/activity")
def list_activity(
    integration_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {
        "items": integration_service.list_activity(
            session, org, integration_id=integration_id, limit=limit
        )
    }


@router.get("")
def list_integrations(
    category: str | None = None,
    is_enabled: bool | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {
        "items": integration_service.list_integrations(
            session, org, category=category, is_enabled=is_enabled
        )
    }


@router.post("")
def create_integration(
    body: IntegrationCreateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return integration_service.create_integration(
        session,
        org,
        name=body.name,
        provider_key=body.provider_key,
        description=body.description,
        api_base_url=body.api_base_url,
        auth_type=body.auth_type,
        config=body.config,
        credentials=body.credentials,
        is_enabled=body.is_enabled,
    )


@router.get("/{integration_id}")
def get_integration(
    integration_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return integration_service.get_integration(session, org, integration_id)


@router.patch("/{integration_id}")
def update_integration(
    integration_id: uuid.UUID,
    body: IntegrationUpdateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return integration_service.update_integration(
        session,
        org,
        integration_id,
        name=body.name,
        description=body.description,
        api_base_url=body.api_base_url,
        auth_type=body.auth_type,
        config=body.config,
        credentials=body.credentials,
        is_enabled=body.is_enabled,
    )


@router.post("/{integration_id}/test-connection")
def test_connection(
    integration_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return integration_service.test_connection(session, org, integration_id)


@router.get("/{integration_id}/mappings")
def list_mappings(
    integration_id: uuid.UUID,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return {"items": integration_service.list_field_mappings(session, org, integration_id)}


@router.post("/{integration_id}/mappings")
def create_mapping(
    integration_id: uuid.UUID,
    body: MappingCreateBody,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    return integration_service.create_field_mapping(
        session, org, integration_id, name=body.name, mappings=body.mappings
    )


@router.post("/{integration_id}/sync")
def start_sync(
    integration_id: uuid.UUID,
    body: SyncStartBody | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict:
    payload = body or SyncStartBody()
    return integration_sync.start_sync(
        session,
        org,
        integration_id,
        direction=payload.direction,
        idempotency_key=payload.idempotency_key,
    )
