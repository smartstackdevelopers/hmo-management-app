"""F7.3 backup orchestration."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.backup import access as backup_access
from app.backup.constants import BACKUP_STATUSES, BACKUP_TYPES, RETENTION_TIERS
from app.backup.database_runner import pg_dump_available, run_config_manifest, run_pg_dump, verify_pg_dump_archive
from app.backup.files_runner import write_files_manifest
from app.backup.integrity import sha256_file, verify_checksum
from app.backup import drill as drill_mod
from app.core.config import Settings, get_settings
from app.db.models.backup import BackupRetentionSetting, BackupRun, BackupScheduleConfig, RestoreDrillRun
from app.db.session import get_engine
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _backup_root(settings: Settings) -> Path:
    root = Path(settings.backup_local_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _idempotency_key(backup_type: str, tier: str, moment: datetime | None = None) -> str:
    moment = moment or _now()
    bucket = moment.strftime("%Y-%m-%d-%H") if tier == "daily" else moment.strftime("%Y-%m-%d")
    return f"{backup_type}:{tier}:{bucket}"


def dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    backup_access.require_backup_read(ctx)
    latest = session.scalar(select(BackupRun).order_by(desc(BackupRun.started_at)).limit(1))
    last_ok = session.scalar(
        select(BackupRun)
        .where(BackupRun.status == "verified")
        .order_by(desc(BackupRun.completed_at))
        .limit(1)
    )
    last_fail = session.scalar(
        select(BackupRun)
        .where(BackupRun.status == "failed")
        .order_by(desc(BackupRun.completed_at))
        .limit(1)
    )
    pending = session.scalar(
        select(func.count()).select_from(BackupRun).where(BackupRun.status.in_(("pending", "running")))
    )
    drills = session.scalars(select(RestoreDrillRun).order_by(desc(RestoreDrillRun.started_at)).limit(5)).all()
    settings = get_settings()
    return {
        "backup_enabled": settings.backup_enabled,
        "pg_dump_available": pg_dump_available(),
        "latest_backup": _run_dict(latest) if latest else None,
        "last_successful_backup": _run_dict(last_ok) if last_ok else None,
        "last_failed_backup": _run_dict(last_fail) if last_fail else None,
        "pending_jobs": pending or 0,
        "recent_drills": [_drill_dict(d) for d in drills],
        "storage": {
            "local_root_configured": bool(settings.backup_local_root),
            "backup_s3_bucket_configured": bool(settings.backup_s3_bucket),
            "encryption_note": "Use SSE-S3 or SSE-KMS on backup bucket; separate from application bucket",
        },
        "rpo_status": "pending_approval",
        "rto_status": "pending_approval",
        "outstanding_issues": _outstanding_issues(session, settings),
    }


def _outstanding_issues(session: Session, settings: Settings) -> list[str]:
    issues: list[str] = []
    if not settings.backup_enabled:
        issues.append("BACKUP_ENABLED is false — scheduled jobs will not run backups.")
    if settings.is_production and not settings.backup_s3_bucket:
        issues.append("Configure BACKUP_S3_BUCKET for off-host backup storage in production.")
    if not pg_dump_available():
        issues.append("pg_dump not found on API host — database backups require PostgreSQL client tools.")
    if not session.scalar(select(BackupRun).where(BackupRun.status == "verified").limit(1)):
        issues.append("No verified backup on record yet — run a backup and verification.")
    return issues


def _run_dict(row: BackupRun | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": str(row.id),
        "backup_type": row.backup_type,
        "scope": row.scope,
        "status": row.status,
        "verification_status": row.verification_status,
        "retention_tier": row.retention_tier,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "size_bytes": row.size_bytes,
        "storage_location": row.storage_location,
        "checksum_sha256": row.checksum_sha256,
        "error_message": row.error_message,
    }


def _drill_dict(row: RestoreDrillRun) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "status": row.status,
        "environment_label": row.environment_label,
        "duration_seconds": row.duration_seconds,
        "rto_seconds_measured": row.rto_seconds_measured,
        "started_at": row.started_at.isoformat() if row.started_at else None,
    }


def list_runs(session: Session, ctx: OrganisationContext, limit: int = 50) -> list[dict[str, Any]]:
    backup_access.require_backup_read(ctx)
    rows = session.scalars(select(BackupRun).order_by(desc(BackupRun.started_at)).limit(limit)).all()
    return [_run_dict(r) for r in rows if r]


def list_schedules(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    backup_access.require_backup_read(ctx)
    rows = session.scalars(select(BackupScheduleConfig).order_by(BackupScheduleConfig.backup_type)).all()
    return [
        {
            "id": str(r.id),
            "backup_type": r.backup_type,
            "retention_tier": r.retention_tier,
            "cron_expression": r.cron_expression,
            "enabled": r.enabled,
        }
        for r in rows
    ]


def list_retention(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    backup_access.require_backup_read(ctx)
    rows = session.scalars(select(BackupRetentionSetting)).all()
    return [
        {
            "retention_tier": r.retention_tier,
            "keep_count": r.keep_count,
            "notes": r.notes,
            "approved_by_label": r.approved_by_label,
        }
        for r in rows
    ]


def start_backup(
    session: Session,
    ctx: OrganisationContext,
    *,
    backup_type: str,
    retention_tier: str = "daily",
    organisation_id: uuid.UUID | None = None,
    force: bool = False,
) -> dict[str, Any]:
    backup_access.require_backup_manage(ctx)
    settings = get_settings()
    if backup_type not in BACKUP_TYPES:
        raise HTTPException(status_code=400, detail="Invalid backup type")
    if retention_tier not in RETENTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid retention tier")

    key = _idempotency_key(backup_type, retention_tier)
    existing = session.scalar(select(BackupRun).where(BackupRun.idempotency_key == key))
    if existing and not force:
        if existing.status in ("completed", "verified", "running", "verifying"):
            return {"duplicate": True, "backup": _run_dict(existing)}

    run = BackupRun(
        backup_type=backup_type,
        scope="organisation" if organisation_id else "platform",
        organisation_id=organisation_id,
        status="running",
        retention_tier=retention_tier,
        started_at=_now(),
        idempotency_key=key if not force else f"{key}:{uuid.uuid4().hex[:8]}",
    )
    session.add(run)
    session.flush()

    try:
        path = _execute_backup(session, settings, run)
        run.size_bytes = path.stat().st_size
        run.storage_location = str(path.relative_to(_backup_root(settings)))
        run.completed_at = _now()
        if not _verify_backup(run, path):
            run.status = "rejected_incomplete"
            run.verification_status = "failed"
            run.error_message = "Integrity verification failed"
        else:
            run.status = "verified"
            run.verification_status = "passed"
        run.expires_at = _expiry_for_tier(session, retention_tier)
    except Exception as exc:  # noqa: BLE001 — backup failure must be recorded
        run.status = "failed"
        run.error_message = str(exc)[:2000]
        run.completed_at = _now()
        if run.retry_count < settings.backup_max_retries:
            run.retry_count += 1

    session.flush()
    record_event(
        session,
        action=audit_events.BACKUP_RUN_COMPLETE,
        resource_type="backup_run",
        resource_id=run.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS if run.status == "verified" else AuditOutcome.FAILURE,
        summary=f"Backup {run.backup_type} finished with status {run.status}",
        metadata={"verification": run.verification_status},
        raise_on_error=False,
    )
    return {"duplicate": False, "backup": _run_dict(run)}


def _execute_backup(session: Session, settings: Settings, run: BackupRun) -> Path:
    root = _backup_root(settings)
    stamp = _now().strftime("%Y%m%dT%H%M%SZ")
    filename = f"{run.backup_type}-{stamp}-{run.id.hex[:8]}"
    if run.backup_type == "database":
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        if not settings.backup_database_enabled:
            raise RuntimeError("BACKUP_DATABASE_ENABLED is false")
        if not pg_dump_available():
            raise RuntimeError("pg_dump is not available on this host")
        path = root / "database" / f"{filename}.dump"
        run_pg_dump(settings.database_url, path)
        return path
    if run.backup_type == "files_manifest":
        if not settings.backup_files_enabled:
            raise RuntimeError("BACKUP_FILES_ENABLED is false")
        path = root / "files" / f"{filename}.json"
        write_files_manifest(session, path, organisation_id=run.organisation_id)
        return path
    if run.backup_type == "config_manifest":
        path = root / "config" / f"{filename}.json"
        run_config_manifest(get_engine(), path)
        return path
    raise RuntimeError(f"Unsupported backup type {run.backup_type}")


def _verify_backup(run: BackupRun, path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    run.checksum_sha256 = sha256_file(path)
    if run.backup_type == "database":
        return verify_pg_dump_archive(path)
    return True


def _expiry_for_tier(session: Session, tier: str) -> datetime:
    row = session.scalar(select(BackupRetentionSetting).where(BackupRetentionSetting.retention_tier == tier))
    keep = row.keep_count if row else 7
    return _now() + timedelta(days=keep)


def process_pending_backup_runs(session: Session) -> dict[str, Any]:
    """Worker entry: execute backups created by dispatch_due_backups."""
    settings = get_settings()
    if not settings.backup_enabled:
        return {"processed": 0}
    pending = session.scalars(select(BackupRun).where(BackupRun.status == "pending").limit(5)).all()
    processed = 0
    for run in pending:
        run.status = "running"
        run.started_at = _now()
        session.flush()
        try:
            path = _execute_backup(session, settings, run)
            run.size_bytes = path.stat().st_size
            run.storage_location = str(path.relative_to(_backup_root(settings)))
            run.completed_at = _now()
            if _verify_backup(run, path):
                run.status = "verified"
                run.verification_status = "passed"
                run.expires_at = _expiry_for_tier(session, run.retention_tier)
            else:
                run.status = "rejected_incomplete"
                run.verification_status = "failed"
                run.error_message = "Integrity verification failed"
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.error_message = str(exc)[:2000]
            run.completed_at = _now()
        processed += 1
    session.flush()
    return {"processed": processed}


def dispatch_due_backups(session: Session) -> dict[str, Any]:
    settings = get_settings()
    if not settings.backup_enabled:
        return {"skipped": True, "reason": "backup_disabled"}

    schedules = session.scalars(
        select(BackupScheduleConfig).where(BackupScheduleConfig.enabled.is_(True))
    ).all()
    started = 0
    for sched in schedules:
        key = _idempotency_key(sched.backup_type, sched.retention_tier)
        exists = session.scalar(select(BackupRun).where(BackupRun.idempotency_key == key))
        if exists:
            continue
        run = BackupRun(
            backup_type=sched.backup_type,
            scope="platform",
            status="pending",
            retention_tier=sched.retention_tier,
            idempotency_key=key,
        )
        session.add(run)
        started += 1
    session.flush()
    return {"scheduled_pending": started}


def apply_retention_cleanup(session: Session) -> dict[str, Any]:
    """Delete expired verified backups from local storage only — never delete the newest verified copy per type."""
    settings = get_settings()
    root = _backup_root(settings)
    deleted = 0
    now = _now()
    rows = session.scalars(
        select(BackupRun).where(
            BackupRun.status == "verified",
            BackupRun.expires_at.is_not(None),
            BackupRun.expires_at < now,
        )
    ).all()
    for row in rows:
        latest = session.scalar(
            select(BackupRun)
            .where(BackupRun.backup_type == row.backup_type, BackupRun.status == "verified")
            .order_by(desc(BackupRun.completed_at))
            .limit(1)
        )
        if latest and latest.id == row.id:
            continue
        if row.storage_location:
            path = root / row.storage_location
            if path.is_file():
                path.unlink(missing_ok=True)
        session.delete(row)
        deleted += 1
    session.flush()
    return {"deleted": deleted}


def run_restore_drill(session: Session, ctx: OrganisationContext, backup_run_id: uuid.UUID) -> dict[str, Any]:
    backup_access.require_restore_drill(ctx)
    settings = get_settings()
    if settings.is_production or not settings.backup_restore_drill_allowed:
        raise HTTPException(status_code=403, detail="Restore drills are blocked in production")
    return drill_mod.execute_drill(session, settings, backup_run_id)
