"""F8.9 deep integration hub API — extends /integrations."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.integration_hub import IntegrationWebhookSubscription
from app.db.session import get_session
from app.integration_hub import service
from app.integration_hub.constants import HUB_CATEGORIES
from app.integration_hub.service import _settings
from app.integration_hub.webhooks import verify_signature
from app.integrations.crypto import decrypt_credentials
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/integration-hub", tags=["integration-hub"])


class HubSettingsBody(BaseModel):
    enabled: bool | None = None
    privacy_review_complete: bool | None = None
    rate_limit_per_hour: int | None = Field(default=None, ge=10, le=100000)
    webhook_retry_config: dict[str, Any] | None = None


class RegisterApiBody(BaseModel):
    api_slug: str = Field(min_length=1, max_length=64)
    version: str = "v1"
    description: str | None = None
    auth_method: str = "api_key"
    rate_limit_per_minute: int = 60


class WebhookBody(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    target_url: str = Field(min_length=8, max_length=2048)
    event_types: list[str] = Field(default_factory=list)
    integration_id: uuid.UUID | None = None
    signing_secret: str | None = None
    active: bool = False


class ModuleBindBody(BaseModel):
    integration_id: uuid.UUID | None = None
    active: bool = False


@router.get("/settings")
def get_settings_api(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_READ)
    return service.settings_dict(_settings(session, ctx.organisation_id))


@router.patch("/settings")
def patch_settings_api(
    body: HubSettingsBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.update_settings(session, ctx, body.model_dump(exclude_unset=True))
    return service.settings_dict(row)


@router.get("/dashboard")
def dashboard_api(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> dict[str, Any]:
    return service.deep_dashboard(session, ctx)


@router.get("/categories")
def categories_api(ctx: OrganisationContext = Depends(get_organisation_context)) -> list[dict[str, str]]:
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_READ)
    return [{"slug": s, "label": label} for s, label in HUB_CATEGORIES]


@router.get("/providers")
def providers_api(
    category: str | None = Query(default=None),
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> list[dict[str, Any]]:
    return service.list_providers(session, ctx, category)


@router.post("/apis")
def register_api_api(
    body: RegisterApiBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.register_api(session, ctx, body.model_dump())
    return {"id": str(row.id), "api_slug": row.api_slug, "version": row.version}


@router.post("/webhooks")
def create_webhook_api(
    body: WebhookBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.create_webhook(session, ctx, body.model_dump())
    return {"id": str(row.id), "active": row.active, "name": row.name}


@router.post("/webhooks/{subscription_id}/inbound")
async def inbound_webhook_api(
    subscription_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
    x_hub_signature: str | None = Header(default=None, alias="X-Hub-Signature"),
    x_event_type: str = Header(default="integration.event", alias="X-Event-Type"),
) -> dict[str, Any]:
    """Sandbox/test inbound receiver — requires organisation auth and valid signature when configured."""
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_WEBHOOKS)
    service.assert_addon(session, get_settings(), ctx.organisation_id)
    raw = await request.body()
    sub = session.get(IntegrationWebhookSubscription, subscription_id)
    if sub is None or sub.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    secret: str | None = None
    if sub.signing_secret_encrypted:
        secret = decrypt_credentials(sub.signing_secret_encrypted).get("signing_secret")
    if not secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Signing secret required for inbound verification")
    verified = verify_signature(raw, x_hub_signature, secret)
    row = service.record_inbound_webhook(session, ctx, subscription_id, x_event_type, raw, verified)
    return {"id": str(row.id), "status": row.status, "idempotency_key": row.idempotency_key}


@router.get("/health")
def health_api(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> list[dict[str, Any]]:
    return service.health_monitor(session, ctx)


@router.get("/module-bindings")
def list_bindings_api(session: Session = Depends(get_session), ctx: OrganisationContext = Depends(get_organisation_context)) -> list[dict[str, Any]]:
    return service.list_module_bindings(session, ctx)


@router.put("/module-bindings/{module_key}")
def bind_module_api(
    module_key: str,
    body: ModuleBindBody,
    session: Session = Depends(get_session),
    ctx: OrganisationContext = Depends(get_organisation_context),
) -> dict[str, Any]:
    row = service.bind_module(session, ctx, module_key, body.integration_id, body.active)
    return {"module_key": row.hmore_module_key, "integration_id": str(row.integration_id) if row.integration_id else None, "active": row.active}
