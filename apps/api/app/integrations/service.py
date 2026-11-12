"""Integration registry CRUD, health tests, mappings, and dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.secrets import redact_mapping
from app.db.models.integrations import (
    Integration,
    IntegrationActivityLog,
    IntegrationFieldMapping,
    IntegrationSyncJob,
)
from app.integrations import access
from app.integrations.connectors.adapters import get_adapter
from app.integrations.constants import AUTH_TYPES, CATEGORIES, PROVIDER_CATALOG
from app.integrations.crypto import decrypt_credentials, encrypt_credentials, public_credentials_view
from app.integrations.mapping import validate_mapping_entries
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_blocked_egress_host(host: str) -> bool:
    """Block obvious SSRF targets (loopback / link-local / cloud metadata / private RFC1918)."""
    import ipaddress
    import socket

    h = (host or "").strip().lower().rstrip(".")
    if not h:
        return True
    if h in {"localhost", "metadata.google.internal"}:
        return True
    if h.endswith(".local") or h.endswith(".internal"):
        return True
    # Literal IPs
    try:
        ip = ipaddress.ip_address(h)
        return bool(
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        )
    except ValueError:
        pass
    # Resolve hostname once; if any address is private/metadata, block.
    try:
        infos = socket.getaddrinfo(h, None)
    except OSError:
        # Unresolvable hosts fail later at connection test; allow registration of public DNS names.
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
            or str(ip) == "169.254.169.254"
        ):
            return True
    return False


def _validate_base_url(url: str | None) -> str | None:
    if url is None or url.strip() == "":
        return None
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"https", "http"}:
        raise HTTPException(status_code=400, detail="api_base_url must be http(s)")
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(status_code=400, detail="Non-local api_base_url must use HTTPS")
    # Local HTTP allowed for developer connectors; block private/metadata HTTPS SSRF targets.
    if parsed.scheme == "https" and _is_blocked_egress_host(host):
        raise HTTPException(status_code=400, detail="api_base_url host is not allowed (private or metadata)")
    return cleaned.rstrip("/")


def _log_activity(
    session: Session,
    ctx: OrganisationContext,
    *,
    integration_id: uuid.UUID | None,
    action: str,
    summary: str,
    details: dict[str, Any] | None = None,
    outcome: str = "success",
) -> None:
    session.add(
        IntegrationActivityLog(
            organisation_id=ctx.organisation_id,
            integration_id=integration_id,
            action=action,
            summary=summary[:500],
            details=redact_mapping(details or {}),
            actor_user_id=ctx.user_id,
            outcome=outcome,
        )
    )


def integration_to_dict(row: Integration) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "provider_key": row.provider_key,
        "provider_name": row.provider_name,
        "category": row.category,
        "description": row.description,
        "organisation_id": str(row.organisation_id),
        "api_base_url": row.api_base_url,
        "auth_type": row.auth_type,
        "config": redact_mapping(row.config_json or {}),
        "credentials": public_credentials_view(row.credentials_meta),
        "connection_status": row.connection_status,
        "is_enabled": row.is_enabled,
        "health_status": row.health_status,
        "last_connection_check_at": row.last_connection_check_at.isoformat()
        if row.last_connection_check_at
        else None,
        "last_successful_sync_at": row.last_successful_sync_at.isoformat()
        if row.last_successful_sync_at
        else None,
        "last_failed_sync_at": row.last_failed_sync_at.isoformat() if row.last_failed_sync_at else None,
        "last_error": row.last_error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def provider_catalog() -> list[dict[str, str]]:
    return [
        {"provider_key": key, **value}
        for key, value in PROVIDER_CATALOG.items()
    ]


def create_integration(
    session: Session,
    ctx: OrganisationContext,
    *,
    name: str,
    provider_key: str,
    description: str | None = None,
    api_base_url: str | None = None,
    auth_type: str = "api_key",
    config: dict[str, Any] | None = None,
    credentials: dict[str, Any] | None = None,
    is_enabled: bool = True,
) -> dict[str, Any]:
    access.require_integrations_manage(ctx)
    catalog = PROVIDER_CATALOG.get(provider_key)
    if catalog is None:
        raise HTTPException(status_code=400, detail="Unknown provider_key")
    if auth_type not in AUTH_TYPES:
        raise HTTPException(status_code=400, detail="Invalid auth_type")
    if catalog["category"] not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    base = _validate_base_url(api_base_url)
    ciphertext, meta = encrypt_credentials(credentials)
    status = "configured" if (ciphertext or auth_type == "none") else "not_configured"
    if not is_enabled:
        status = "disabled"
    row = Integration(
        organisation_id=ctx.organisation_id,
        name=name.strip()[:200],
        provider_key=provider_key,
        provider_name=catalog["provider_name"],
        category=catalog["category"],
        description=description or catalog.get("description"),
        api_base_url=base,
        auth_type=auth_type,
        config_json=config or {},
        credentials_encrypted=ciphertext,
        credentials_meta=meta,
        connection_status=status,
        is_enabled=is_enabled,
        health_status="unknown",
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Provider already configured for this organisation") from exc
    _log_activity(
        session,
        ctx,
        integration_id=row.id,
        action="integration.create",
        summary=f"Created integration {row.name}",
        details={"provider_key": provider_key},
    )
    record_event(
        session,
        action=audit_events.INTEGRATION_CREATE,
        resource_type="integration",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Created integration {row.name}",
        metadata={"provider_key": provider_key},
        raise_on_error=False,
    )
    return integration_to_dict(row)


def update_integration(
    session: Session,
    ctx: OrganisationContext,
    integration_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    api_base_url: str | None = None,
    auth_type: str | None = None,
    config: dict[str, Any] | None = None,
    credentials: dict[str, Any] | None = None,
    is_enabled: bool | None = None,
) -> dict[str, Any]:
    access.require_integrations_manage(ctx)
    row = _get_org_integration(session, ctx, integration_id)
    if name is not None:
        row.name = name.strip()[:200]
    if description is not None:
        row.description = description
    if api_base_url is not None:
        row.api_base_url = _validate_base_url(api_base_url)
    if auth_type is not None:
        if auth_type not in AUTH_TYPES:
            raise HTTPException(status_code=400, detail="Invalid auth_type")
        row.auth_type = auth_type
    if config is not None:
        # Never accept secret keys in config_json
        if any(k in config for k in ("api_key", "client_secret", "password", "bearer_token")):
            raise HTTPException(status_code=400, detail="Secrets must be sent in credentials, not config")
        row.config_json = config
    if credentials is not None:
        ciphertext, meta = encrypt_credentials(credentials)
        if ciphertext:
            row.credentials_encrypted = ciphertext
            row.credentials_meta = meta
    if is_enabled is not None:
        row.is_enabled = is_enabled
        if not is_enabled:
            row.connection_status = "disabled"
        elif row.connection_status == "disabled":
            row.connection_status = "configured" if row.credentials_encrypted or row.auth_type == "none" else "not_configured"
    # Changing config invalidates prior connected status until re-tested
    if row.connection_status == "connected" and (
        name is not None or api_base_url is not None or auth_type is not None or credentials is not None or config is not None
    ):
        row.connection_status = "configured"
        row.health_status = "unknown"
    row.updated_by_user_id = ctx.user_id
    session.flush()
    _log_activity(
        session,
        ctx,
        integration_id=row.id,
        action="integration.update",
        summary=f"Updated integration {row.name}",
    )
    record_event(
        session,
        action=audit_events.INTEGRATION_UPDATE,
        resource_type="integration",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Updated integration {row.name}",
        raise_on_error=False,
    )
    return integration_to_dict(row)


def _get_org_integration(session: Session, ctx: OrganisationContext, integration_id: uuid.UUID) -> Integration:
    row = session.get(Integration, integration_id)
    if row is None or row.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Integration not found")
    return row


def list_integrations(
    session: Session,
    ctx: OrganisationContext,
    *,
    category: str | None = None,
    is_enabled: bool | None = None,
) -> list[dict[str, Any]]:
    access.require_integrations_read(ctx)
    stmt = select(Integration).where(Integration.organisation_id == ctx.organisation_id)
    if category:
        stmt = stmt.where(Integration.category == category)
    if is_enabled is not None:
        stmt = stmt.where(Integration.is_enabled.is_(is_enabled))
    rows = session.scalars(stmt.order_by(Integration.created_at.desc())).all()
    return [integration_to_dict(r) for r in rows]


def get_integration(session: Session, ctx: OrganisationContext, integration_id: uuid.UUID) -> dict[str, Any]:
    access.require_integrations_read(ctx)
    return integration_to_dict(_get_org_integration(session, ctx, integration_id))


def test_connection(session: Session, ctx: OrganisationContext, integration_id: uuid.UUID) -> dict[str, Any]:
    access.require_integrations_manage(ctx)
    row = _get_org_integration(session, ctx, integration_id)
    if not row.is_enabled:
        raise HTTPException(status_code=400, detail="Integration is disabled")
    adapter = get_adapter(row.provider_key)
    secrets = decrypt_credentials(row.credentials_encrypted)
    timeout = float((row.config_json or {}).get("timeout_seconds") or 10)
    result = adapter.test_connection(
        base_url=row.api_base_url,
        auth_type=row.auth_type,
        config=row.config_json or {},
        credentials=secrets,
        timeout_seconds=timeout,
    )
    row.last_connection_check_at = _now()
    if result.ok:
        row.connection_status = "connected"
        row.health_status = "healthy"
        row.last_error = None
        outcome = "success"
    else:
        row.connection_status = result.status if result.status in {"failed", "not_configured"} else "failed"
        row.health_status = "unhealthy"
        row.last_error = result.detail[:2000]
        outcome = "failure"
    session.flush()
    _log_activity(
        session,
        ctx,
        integration_id=row.id,
        action="integration.connection_test",
        summary=result.detail[:500],
        details={"http_status": result.http_status, "latency_ms": result.latency_ms},
        outcome=outcome,
    )
    record_event(
        session,
        action=audit_events.INTEGRATION_CONNECTION_TEST,
        resource_type="integration",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS if result.ok else AuditOutcome.FAILURE,
        summary=result.detail[:255],
        metadata={"status": result.status},
        raise_on_error=False,
    )
    return {
        "integration": integration_to_dict(row),
        "test": {
            "ok": result.ok,
            "status": result.status,
            "detail": result.detail,
            "http_status": result.http_status,
            "latency_ms": result.latency_ms,
        },
    }


def create_field_mapping(
    session: Session,
    ctx: OrganisationContext,
    integration_id: uuid.UUID,
    *,
    name: str,
    mappings: list[dict[str, Any]],
) -> dict[str, Any]:
    access.require_integrations_manage(ctx)
    row = _get_org_integration(session, ctx, integration_id)
    cleaned = validate_mapping_entries(mappings)
    latest = session.scalar(
        select(func.max(IntegrationFieldMapping.version)).where(
            IntegrationFieldMapping.organisation_id == ctx.organisation_id,
            IntegrationFieldMapping.integration_id == row.id,
        )
    )
    version = int(latest or 0) + 1
    # deactivate previous active versions
    prev = session.scalars(
        select(IntegrationFieldMapping).where(
            IntegrationFieldMapping.organisation_id == ctx.organisation_id,
            IntegrationFieldMapping.integration_id == row.id,
            IntegrationFieldMapping.is_active.is_(True),
        )
    ).all()
    for p in prev:
        p.is_active = False
    mapping = IntegrationFieldMapping(
        organisation_id=ctx.organisation_id,
        integration_id=row.id,
        version=version,
        name=name.strip()[:200] or "default",
        mappings_json=cleaned,
        is_active=True,
        created_by_user_id=ctx.user_id,
    )
    session.add(mapping)
    session.flush()
    _log_activity(
        session,
        ctx,
        integration_id=row.id,
        action="integration.mapping.create",
        summary=f"Created mapping v{version}",
        details={"version": version, "fields": len(cleaned)},
    )
    record_event(
        session,
        action=audit_events.INTEGRATION_MAPPING_UPDATE,
        resource_type="integration_field_mapping",
        resource_id=mapping.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Mapping v{version} for {row.name}",
        raise_on_error=False,
    )
    return {
        "id": str(mapping.id),
        "integration_id": str(row.id),
        "version": mapping.version,
        "name": mapping.name,
        "mappings": mapping.mappings_json,
        "is_active": mapping.is_active,
        "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
    }


def list_field_mappings(
    session: Session, ctx: OrganisationContext, integration_id: uuid.UUID
) -> list[dict[str, Any]]:
    access.require_integrations_read(ctx)
    row = _get_org_integration(session, ctx, integration_id)
    maps = session.scalars(
        select(IntegrationFieldMapping)
        .where(
            IntegrationFieldMapping.organisation_id == ctx.organisation_id,
            IntegrationFieldMapping.integration_id == row.id,
        )
        .order_by(IntegrationFieldMapping.version.desc())
    ).all()
    return [
        {
            "id": str(m.id),
            "version": m.version,
            "name": m.name,
            "mappings": m.mappings_json,
            "is_active": m.is_active,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in maps
    ]


def list_activity(
    session: Session,
    ctx: OrganisationContext,
    *,
    integration_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    access.require_integrations_read(ctx)
    stmt = select(IntegrationActivityLog).where(IntegrationActivityLog.organisation_id == ctx.organisation_id)
    if integration_id:
        stmt = stmt.where(IntegrationActivityLog.integration_id == integration_id)
    rows = session.scalars(stmt.order_by(IntegrationActivityLog.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": str(r.id),
            "integration_id": str(r.integration_id) if r.integration_id else None,
            "action": r.action,
            "summary": r.summary,
            "details": r.details,
            "outcome": r.outcome,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def list_sync_jobs(
    session: Session,
    ctx: OrganisationContext,
    *,
    integration_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    access.require_integrations_read(ctx)
    stmt = select(IntegrationSyncJob).where(IntegrationSyncJob.organisation_id == ctx.organisation_id)
    if integration_id:
        stmt = stmt.where(IntegrationSyncJob.integration_id == integration_id)
    if status:
        stmt = stmt.where(IntegrationSyncJob.status == status)
    rows = session.scalars(stmt.order_by(IntegrationSyncJob.created_at.desc()).limit(limit)).all()
    return [sync_job_to_dict(r) for r in rows]


def sync_job_to_dict(row: IntegrationSyncJob) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "integration_id": str(row.integration_id),
        "direction": row.direction,
        "status": row.status,
        "success_count": row.success_count,
        "failure_count": row.failure_count,
        "error_details": row.error_details,
        "result_summary": row.result_summary,
        "cancel_requested": row.cancel_requested,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    access.require_integrations_read(ctx)
    org = ctx.organisation_id
    total = int(session.scalar(select(func.count()).select_from(Integration).where(Integration.organisation_id == org)) or 0)
    active = int(
        session.scalar(
            select(func.count())
            .select_from(Integration)
            .where(Integration.organisation_id == org, Integration.is_enabled.is_(True))
        )
        or 0
    )
    connected = int(
        session.scalar(
            select(func.count())
            .select_from(Integration)
            .where(Integration.organisation_id == org, Integration.connection_status == "connected")
        )
        or 0
    )
    failed = int(
        session.scalar(
            select(func.count())
            .select_from(Integration)
            .where(Integration.organisation_id == org, Integration.connection_status == "failed")
        )
        or 0
    )
    failed_syncs = int(
        session.scalar(
            select(func.count())
            .select_from(IntegrationSyncJob)
            .where(IntegrationSyncJob.organisation_id == org, IntegrationSyncJob.status == "failed")
        )
        or 0
    )
    return {
        "generated_at": _now().isoformat(),
        "total_integrations": total,
        "active_integrations": active,
        "disabled_integrations": max(0, total - active),
        "connected_integrations": connected,
        "failed_connections": failed,
        "failed_sync_jobs": failed_syncs,
        "providers": provider_catalog(),
        "recent_syncs": list_sync_jobs(session, ctx, limit=8),
        "recent_activity": list_activity(session, ctx, limit=8),
    }
