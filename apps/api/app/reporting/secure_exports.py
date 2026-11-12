"""Secure stored report exports with authorised download."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.file_metadata import FileMetadata
from app.db.models.reporting_analytics import ReportExport
from app.rbac.permissions import Permission
from app.reporting.access import (
    require_export_csv,
    require_export_excel,
    require_export_pdf,
)
from app.storage.factory import get_storage_backend
from app.storage.keys import build_object_key
from app.tenancy.context import OrganisationContext

CONTENT_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _require_format(ctx: OrganisationContext, fmt: str) -> None:
    if fmt == "csv":
        require_export_csv(ctx)
    elif fmt == "pdf":
        require_export_pdf(ctx)
    else:
        require_export_excel(ctx)


def store_report_export(
    session: Session,
    ctx: OrganisationContext,
    *,
    category: str,
    export_format: str,
    title: str,
    body: bytes,
    filters: dict[str, Any] | None = None,
    row_count: int = 0,
    allowed_user_ids: list[str] | None = None,
    created_by_user_id: uuid.UUID | None = None,
) -> ReportExport:
    _require_format(ctx, export_format)
    filename = f"hmore-{category}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.{export_format}"
    key = build_object_key(organisation_id=ctx.organisation_id, original_filename=filename)
    backend = get_storage_backend()
    content_type = CONTENT_TYPES.get(export_format, "application/octet-stream")
    checksum = hashlib.sha256(body).hexdigest()
    backend.put_bytes(key=key, data=body, content_type=content_type)
    meta = FileMetadata(
        organisation_id=ctx.organisation_id,
        storage_key=key,
        storage_provider=backend.provider_name,
        original_filename=filename,
        content_type=content_type.split(";")[0],
        size_bytes=len(body),
        checksum_sha256=checksum,
        status="active",
        uploaded_by_user_id=created_by_user_id or ctx.user_id,
        resource_type="report_export",
        resource_id=category,
    )
    session.add(meta)
    session.flush()
    export = ReportExport(
        organisation_id=ctx.organisation_id,
        report_category=category,
        export_format=export_format,
        title=title,
        filters_json=filters or {},
        row_count=row_count,
        file_metadata_id=meta.id,
        created_by_user_id=created_by_user_id or ctx.user_id,
        status="ready",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        allowed_user_ids=allowed_user_ids or [str(created_by_user_id or ctx.user_id)],
    )
    session.add(export)
    session.flush()
    record_event(
        session,
        action=audit_events.REPORTS_EXPORT_STORE,
        resource_type="report_export",
        resource_id=export.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Stored {category} export as {export_format}",
        metadata={"rows": row_count, "bytes": len(body)},
        raise_on_error=False,
    )
    return export


def can_download(session: Session, ctx: OrganisationContext, export: ReportExport) -> bool:
    if export.organisation_id != ctx.organisation_id:
        return False
    if export.status != "ready":
        return False
    if export.expires_at and export.expires_at < datetime.now(timezone.utc):
        return False
    if ctx.authorization.has_permission(Permission.REPORTS_SCHEDULE_MANAGE):
        return True
    if export.created_by_user_id and export.created_by_user_id == ctx.user_id:
        return True
    allowed = {str(x) for x in (export.allowed_user_ids or [])}
    return str(ctx.user_id) in allowed


def get_export_bytes(session: Session, ctx: OrganisationContext, export_id: uuid.UUID) -> tuple[ReportExport, FileMetadata, bytes]:
    export = session.get(ReportExport, export_id)
    if export is None or export.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    if not can_download(session, ctx, export):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to download this export")
    meta = session.get(FileMetadata, export.file_metadata_id)
    if meta is None or meta.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file missing")
    backend = get_storage_backend()
    data = backend.get_bytes(key=meta.storage_key)
    record_event(
        session,
        action=audit_events.REPORTS_EXPORT_DOWNLOAD,
        resource_type="report_export",
        resource_id=export.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Downloaded {export.report_category} {export.export_format}",
        raise_on_error=False,
    )
    return export, meta, data


def export_to_dict(row: ReportExport) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "report_category": row.report_category,
        "export_format": row.export_format,
        "title": row.title,
        "row_count": row.row_count,
        "status": row.status,
        "filters": row.filters_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "download_path": f"/api/v1/reports/exports/{row.id}/download",
    }
