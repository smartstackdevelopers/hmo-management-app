"""F8.9 deep integration hub — wraps F6.4 integrations service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.hub_module_binding import HubModuleBinding
from app.db.models.integration_hub import (
    IntegrationApiUsageLog,
    IntegrationHubProviderDirectory,
    IntegrationRegisteredApi,
    IntegrationWebhookDelivery,
    IntegrationWebhookSubscription,
    OrganisationIntegrationHubSettings,
)
from app.db.models.integrations import Integration, IntegrationActivityLog, IntegrationSyncJob
from app.integration_hub.constants import ADDON_DISCLAIMER, FOUNDATION_PROVIDERS, HMORE_MODULE_KEYS, HUB_CATEGORIES
from app.integration_hub.webhooks import payload_hash
from app.integrations import service as integrations_service
from app.integrations.crypto import encrypt_credentials
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _settings(session: Session, org_id: UUID) -> OrganisationIntegrationHubSettings:
    row = session.scalars(
        select(OrganisationIntegrationHubSettings).where(OrganisationIntegrationHubSettings.organisation_id == org_id)
    ).first()
    if row is None:
        row = OrganisationIntegrationHubSettings(organisation_id=org_id)
        session.add(row)
        session.flush()
    return row


def assert_addon(session: Session, settings: Settings, org_id: UUID) -> OrganisationIntegrationHubSettings:
    if not settings.integration_hub_global_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Integration hub add-on disabled platform-wide")
    row = _settings(session, org_id)
    if not row.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Integration hub disabled for organisation")
    return row


def settings_dict(row: OrganisationIntegrationHubSettings) -> dict[str, Any]:
    return {
        "organisation_id": str(row.organisation_id),
        "enabled": row.enabled,
        "privacy_review_complete": row.privacy_review_complete,
        "rate_limit_per_hour": row.rate_limit_per_hour,
        "webhook_retry_config": row.webhook_retry_config,
        "disclaimer": ADDON_DISCLAIMER,
    }


def update_settings(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> OrganisationIntegrationHubSettings:
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_MANAGE)
    row = assert_addon(session, get_settings(), ctx.organisation_id)
    for key in ("enabled", "privacy_review_complete"):
        if data.get(key) is not None:
            setattr(row, key, bool(data[key]))
    if data.get("rate_limit_per_hour") is not None:
        row.rate_limit_per_hour = int(data["rate_limit_per_hour"])
    if data.get("webhook_retry_config") is not None:
        row.webhook_retry_config = data["webhook_retry_config"]
    session.flush()
    record_event(
        session,
        action=audit_events.INTEGRATION_HUB_SETTINGS_UPDATE,
        resource_type="integration_hub_settings",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Integration hub settings updated",
    )
    return row


def seed_provider_directory(session: Session, org_id: UUID) -> None:
    if session.scalar(select(func.count()).select_from(IntegrationHubProviderDirectory).where(IntegrationHubProviderDirectory.organisation_id == org_id)):
        return
    for key, category, name in FOUNDATION_PROVIDERS:
        session.add(
            IntegrationHubProviderDirectory(
                organisation_id=org_id,
                provider_key=key,
                category_slug=category,
                provider_name=name,
                description="Sandbox/foundation only — not a live connection.",
                auth_methods=["api_key", "oauth2"],
                sandbox_only=True,
                active=True,
            )
        )
    session.flush()


def deep_dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_READ)
    assert_addon(session, get_settings(), ctx.organisation_id)
    base = integrations_service.dashboard(session, ctx)
    org = ctx.organisation_id
    webhooks = session.scalar(select(func.count()).select_from(IntegrationWebhookSubscription).where(IntegrationWebhookSubscription.organisation_id == org)) or 0
    deliveries_failed = (
        session.scalar(
            select(func.count()).select_from(IntegrationWebhookDelivery).where(
                IntegrationWebhookDelivery.organisation_id == org,
                IntegrationWebhookDelivery.status == "failed",
            )
        )
        or 0
    )
    api_calls_hour = (
        session.scalar(
            select(func.count()).select_from(IntegrationApiUsageLog).where(
                IntegrationApiUsageLog.organisation_id == org,
                IntegrationApiUsageLog.created_at >= _now() - timedelta(hours=1),
            )
        )
        or 0
    )
    bindings = session.scalar(select(func.count()).select_from(HubModuleBinding).where(HubModuleBinding.organisation_id == org, HubModuleBinding.active.is_(True))) or 0
    return {
        **base,
        "webhook_subscriptions": int(webhooks),
        "webhook_failures": int(deliveries_failed),
        "api_calls_last_hour": int(api_calls_hour),
        "active_module_bindings": int(bindings),
        "categories_count": len(HUB_CATEGORIES),
        "disclaimer": ADDON_DISCLAIMER,
    }


def list_providers(session: Session, ctx: OrganisationContext, category: str | None) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_READ)
    assert_addon(session, get_settings(), ctx.organisation_id)
    seed_provider_directory(session, ctx.organisation_id)
    q = select(IntegrationHubProviderDirectory).where(
        IntegrationHubProviderDirectory.organisation_id == ctx.organisation_id,
        IntegrationHubProviderDirectory.active.is_(True),
    )
    if category:
        q = q.where(IntegrationHubProviderDirectory.category_slug == category)
    rows = session.scalars(q).all()
    return [
        {
            "provider_key": r.provider_key,
            "provider_name": r.provider_name,
            "category_slug": r.category_slug,
            "sandbox_only": r.sandbox_only,
            "auth_methods": r.auth_methods,
        }
        for r in rows
    ]


def register_api(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> IntegrationRegisteredApi:
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_MANAGE)
    assert_addon(session, get_settings(), ctx.organisation_id)
    row = IntegrationRegisteredApi(
        organisation_id=ctx.organisation_id,
        api_slug=data["api_slug"],
        version=data.get("version", "v1"),
        description=data.get("description"),
        auth_method=data.get("auth_method", "api_key"),
        rate_limit_per_minute=int(data.get("rate_limit_per_minute", 60)),
        active=bool(data.get("active", True)),
    )
    session.add(row)
    session.flush()
    return row


def create_webhook(session: Session, ctx: OrganisationContext, data: dict[str, Any]) -> IntegrationWebhookSubscription:
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_WEBHOOKS)
    assert_addon(session, get_settings(), ctx.organisation_id)
    secret = data.get("signing_secret")
    encrypted = encrypt_credentials({"signing_secret": secret}) if secret else None
    row = IntegrationWebhookSubscription(
        organisation_id=ctx.organisation_id,
        integration_id=data.get("integration_id"),
        name=data["name"],
        event_types=data.get("event_types") or [],
        target_url=data["target_url"],
        signing_secret_encrypted=encrypted,
        active=bool(data.get("active", False)),
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.INTEGRATION_HUB_WEBHOOK_CREATED,
        resource_type="integration_webhook_subscription",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Webhook subscription created",
    )
    return row


def record_inbound_webhook(
    session: Session,
    ctx: OrganisationContext,
    subscription_id: UUID,
    event_type: str,
    body: bytes,
    verified: bool,
) -> IntegrationWebhookDelivery:
    sub = session.get(IntegrationWebhookSubscription, subscription_id)
    if sub is None or sub.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    if not verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Webhook signature invalid")
    idem = f"in:{payload_hash(body)[:32]}"
    existing = session.scalar(
        select(IntegrationWebhookDelivery).where(
            IntegrationWebhookDelivery.organisation_id == ctx.organisation_id,
            IntegrationWebhookDelivery.idempotency_key == idem,
        )
    )
    if existing:
        return existing
    row = IntegrationWebhookDelivery(
        organisation_id=ctx.organisation_id,
        subscription_id=sub.id,
        event_type=event_type,
        idempotency_key=idem,
        status="received",
        payload_hash=payload_hash(body),
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.INTEGRATION_HUB_WEBHOOK_RECEIVED,
        resource_type="integration_webhook_delivery",
        resource_id=str(row.id),
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value if ctx.role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Inbound webhook accepted",
    )
    return row


def bind_module(session: Session, ctx: OrganisationContext, module_key: str, integration_id: UUID | None, active: bool) -> HubModuleBinding:
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_MANAGE)
    if module_key not in HMORE_MODULE_KEYS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown module key")
    row = session.scalar(
        select(HubModuleBinding).where(
            HubModuleBinding.organisation_id == ctx.organisation_id,
            HubModuleBinding.hmore_module_key == module_key,
        )
    )
    if row is None:
        row = HubModuleBinding(
            organisation_id=ctx.organisation_id,
            hmore_module_key=module_key,
            integration_id=integration_id,
            active=active,
        )
        session.add(row)
    else:
        row.integration_id = integration_id
        row.active = active
    session.flush()
    return row


def log_api_usage(
    session: Session,
    org_id: UUID,
    *,
    method: str,
    path: str,
    status_code: int,
    api_slug: str | None,
    latency_ms: int | None,
) -> None:
    session.add(
        IntegrationApiUsageLog(
            organisation_id=org_id,
            api_slug=api_slug,
            http_method=method,
            path=path[:500],
            status_code=status_code,
            latency_ms=latency_ms,
        )
    )


def health_monitor(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_REPORTS)
    assert_addon(session, get_settings(), ctx.organisation_id)
    rows = session.scalars(select(Integration).where(Integration.organisation_id == ctx.organisation_id)).all()
    out = []
    for r in rows:
        out.append(
            {
                "integration_id": str(r.id),
                "name": r.name,
                "connection_status": r.connection_status,
                "health_status": r.health_status,
                "last_connection_check_at": r.last_connection_check_at.isoformat() if r.last_connection_check_at else None,
                "last_successful_sync_at": r.last_successful_sync_at.isoformat() if r.last_successful_sync_at else None,
                "last_error": (r.last_error or "")[:200] or None,
                "connected_claim": r.connection_status == "connected",
            }
        )
    return out


def list_module_bindings(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    require_permission(ctx.authorization, Permission.INTEGRATION_HUB_READ)
    rows = session.scalars(select(HubModuleBinding).where(HubModuleBinding.organisation_id == ctx.organisation_id)).all()
    return [
        {
            "module_key": r.hmore_module_key,
            "integration_id": str(r.integration_id) if r.integration_id else None,
            "active": r.active,
        }
        for r in rows
    ]
