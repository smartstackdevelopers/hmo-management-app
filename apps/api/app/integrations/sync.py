"""Controlled sync job foundation (Celery-ready, idempotent)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.integrations import Integration, IntegrationSyncJob
from app.integrations import access, service as integration_service
from app.integrations.connectors.adapters import get_adapter
from app.integrations.constants import SYNC_DIRECTIONS
from app.integrations.crypto import decrypt_credentials
from app.tenancy.context import OrganisationContext

logger = logging.getLogger("hmore.integrations.sync")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def start_sync(
    session: Session,
    ctx: OrganisationContext,
    integration_id: uuid.UUID,
    *,
    direction: str = "health_check",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    access.require_integrations_manage(ctx)
    if direction not in SYNC_DIRECTIONS:
        raise HTTPException(status_code=400, detail="Invalid sync direction")
    row = integration_service._get_org_integration(session, ctx, integration_id)  # noqa: SLF001
    if not row.is_enabled:
        raise HTTPException(status_code=400, detail="Integration is disabled")
    # Real partner import/export is not activated without verified credentials + API specs.
    if direction in {"import", "export", "bidirectional"} and row.connection_status != "connected":
        raise HTTPException(
            status_code=400,
            detail="Import/export sync requires a successful connection test first",
        )
    key = idempotency_key or f"sync:{row.id}:{direction}:{_now().strftime('%Y%m%d%H%M')}"
    existing = session.scalar(
        select(IntegrationSyncJob).where(
            IntegrationSyncJob.organisation_id == ctx.organisation_id,
            IntegrationSyncJob.idempotency_key == key,
        )
    )
    if existing is not None:
        return {"ok": True, "skipped": True, "job": integration_service.sync_job_to_dict(existing)}

    job = IntegrationSyncJob(
        organisation_id=ctx.organisation_id,
        integration_id=row.id,
        direction=direction,
        status="pending",
        idempotency_key=key,
        triggered_by_user_id=ctx.user_id,
    )
    session.add(job)
    try:
        session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(IntegrationSyncJob).where(
                IntegrationSyncJob.organisation_id == ctx.organisation_id,
                IntegrationSyncJob.idempotency_key == key,
            )
        )
        return {
            "ok": True,
            "skipped": True,
            "job": integration_service.sync_job_to_dict(existing) if existing else None,
        }

    record_event(
        session,
        action=audit_events.INTEGRATION_SYNC_START,
        resource_type="integration_sync_job",
        resource_id=job.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Started {direction} sync for {row.name}",
        raise_on_error=False,
    )
    result = execute_sync_job(session, job.id)
    return result


def execute_sync_job(session: Session, job_id: uuid.UUID) -> dict[str, Any]:
    job = session.get(IntegrationSyncJob, job_id)
    if job is None:
        return {"ok": False, "error": "job_not_found"}
    if job.status in {"succeeded", "cancelled"}:
        return {"ok": True, "skipped": True, "job": integration_service.sync_job_to_dict(job)}
    if job.cancel_requested:
        job.status = "cancelled"
        job.finished_at = _now()
        session.flush()
        return {"ok": True, "cancelled": True, "job": integration_service.sync_job_to_dict(job)}

    integration = session.get(Integration, job.integration_id)
    if integration is None:
        job.status = "failed"
        job.error_details = "Integration missing"
        job.finished_at = _now()
        session.flush()
        return {"ok": False, "error": "integration_missing"}

    job.status = "running"
    job.started_at = _now()
    session.flush()
    try:
        adapter = get_adapter(integration.provider_key)
        secrets = decrypt_credentials(integration.credentials_encrypted)
        timeout = float((integration.config_json or {}).get("timeout_seconds") or 10)
        # Foundation: only health_check path runs live HTTP; other directions stay scaffolding
        # unless already connected and explicitly requested — still uses health for safety.
        sync_result = adapter.health_sync(
            base_url=integration.api_base_url,
            auth_type=integration.auth_type,
            config=integration.config_json or {},
            credentials=secrets,
            timeout_seconds=timeout,
        )
        if job.cancel_requested:
            job.status = "cancelled"
            job.finished_at = _now()
            session.flush()
            return {"ok": True, "cancelled": True, "job": integration_service.sync_job_to_dict(job)}

        job.success_count = sync_result.success_count
        job.failure_count = sync_result.failure_count
        job.result_summary = {
            "detail": sync_result.detail,
            "direction": job.direction,
            "errors": sync_result.errors[:20],
            "note": "Partner record import/export is not activated without verified API specs.",
        }
        if sync_result.failure_count and not sync_result.success_count:
            job.status = "failed"
            job.error_details = sync_result.detail[:2000]
            integration.last_failed_sync_at = _now()
            integration.last_error = sync_result.detail[:2000]
            action = audit_events.INTEGRATION_SYNC_FAIL
            outcome = AuditOutcome.FAILURE
        else:
            job.status = "succeeded"
            integration.last_successful_sync_at = _now()
            integration.last_error = None
            action = audit_events.INTEGRATION_SYNC_COMPLETE
            outcome = AuditOutcome.SUCCESS
        job.finished_at = _now()
        session.flush()
        record_event(
            session,
            action=action,
            resource_type="integration_sync_job",
            resource_id=job.id,
            organisation_id=job.organisation_id,
            outcome=outcome,
            summary=sync_result.detail[:255],
            raise_on_error=False,
        )
        return {"ok": job.status == "succeeded", "job": integration_service.sync_job_to_dict(job)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Integration sync failed job_id=%s", job_id)
        job.status = "failed"
        job.failure_count = max(job.failure_count, 1)
        job.error_details = str(exc)[:2000]
        job.finished_at = _now()
        integration.last_failed_sync_at = _now()
        integration.last_error = str(exc)[:2000]
        session.flush()
        record_event(
            session,
            action=audit_events.INTEGRATION_SYNC_FAIL,
            resource_type="integration_sync_job",
            resource_id=job.id,
            organisation_id=job.organisation_id,
            outcome=AuditOutcome.FAILURE,
            summary=str(exc)[:255],
            raise_on_error=False,
        )
        return {"ok": False, "job": integration_service.sync_job_to_dict(job), "error": str(exc)[:500]}


def request_cancel(session: Session, ctx: OrganisationContext, job_id: uuid.UUID) -> dict[str, Any]:
    access.require_integrations_manage(ctx)
    job = session.get(IntegrationSyncJob, job_id)
    if job is None or job.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status in {"succeeded", "failed", "cancelled"}:
        return integration_service.sync_job_to_dict(job)
    job.cancel_requested = True
    if job.status == "pending":
        job.status = "cancelled"
        job.finished_at = _now()
    session.flush()
    return integration_service.sync_job_to_dict(job)


def dispatch_due_scheduled_syncs(session: Session) -> dict[str, Any]:
    """Foundation placeholder: only enabled integrations with config.auto_sync=true."""
    rows = session.scalars(
        select(Integration).where(
            Integration.is_enabled.is_(True),
            Integration.connection_status == "connected",
        )
    ).all()
    results = []
    for row in rows:
        cfg = row.config_json or {}
        if not cfg.get("auto_sync"):
            continue
        # System-style: create idempotent hourly health sync without user ctx
        key = f"auto:{row.id}:{_now().strftime('%Y%m%d%H')}"
        existing = session.scalar(
            select(IntegrationSyncJob).where(
                IntegrationSyncJob.organisation_id == row.organisation_id,
                IntegrationSyncJob.idempotency_key == key,
            )
        )
        if existing is not None:
            results.append({"skipped": True, "integration_id": str(row.id)})
            continue
        job = IntegrationSyncJob(
            organisation_id=row.organisation_id,
            integration_id=row.id,
            direction="health_check",
            status="pending",
            idempotency_key=key,
        )
        session.add(job)
        try:
            session.flush()
            results.append(execute_sync_job(session, job.id))
        except IntegrityError:
            results.append({"skipped": True, "integration_id": str(row.id)})
        except Exception as exc:  # noqa: BLE001
            results.append({"ok": False, "integration_id": str(row.id), "error": str(exc)[:300]})
    return {"processed": len(results), "results": results}
