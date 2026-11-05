"""Organisation-scoped private file operations with audit integration."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.file_metadata import FileMetadata
from app.records.pagination import offset_limit
from app.storage.factory import get_storage_backend
from app.storage.keys import build_object_key
from app.storage.protocol import StorageBackend
from app.storage.validation import validate_upload
from app.tenancy.context import OrganisationContext
from app.tenancy.isolation import assert_same_organisation

logger = logging.getLogger("hmore.storage")


def _public_view(row: FileMetadata) -> dict[str, Any]:
    """API-safe metadata — never includes storage_key or credentials."""
    return {
        "id": str(row.id),
        "organisation_id": str(row.organisation_id),
        "original_filename": row.original_filename,
        "content_type": row.content_type,
        "size_bytes": row.size_bytes,
        "checksum_sha256": row.checksum_sha256,
        "status": row.status,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "uploaded_by_user_id": (
            str(row.uploaded_by_user_id) if row.uploaded_by_user_id else None
        ),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def upload_file(
    session: Session,
    ctx: OrganisationContext,
    *,
    filename: str | None,
    declared_content_type: str | None,
    data: bytes,
    resource_type: str | None = None,
    resource_id: str | None = None,
    settings: Settings | None = None,
    backend: StorageBackend | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    backend = backend or get_storage_backend()
    try:
        validated = validate_upload(
            settings=settings,
            filename=filename,
            declared_content_type=declared_content_type,
            data=data,
        )
    except HTTPException as exc:
        record_event(
            session,
            action=audit_events.FILE_UPLOAD_REJECTED,
            resource_type="file",
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="File upload rejected by validation",
            metadata={"detail": str(exc.detail), "declared_type": declared_content_type},
            raise_on_error=False,
        )
        raise

    key = build_object_key(
        organisation_id=ctx.organisation_id,
        original_filename=validated.filename,
    )
    checksum = hashlib.sha256(validated.data).hexdigest()
    try:
        backend.put_bytes(
            key=key, data=validated.data, content_type=validated.content_type
        )
    except FileExistsError:
        record_event(
            session,
            action=audit_events.FILE_UPLOAD_FAILURE,
            resource_type="file",
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Storage key collision",
            raise_on_error=False,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Storage key collision; retry"
        )
    except Exception:
        logger.exception("Storage put failed")
        record_event(
            session,
            action=audit_events.FILE_UPLOAD_FAILURE,
            resource_type="file",
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Storage provider write failed",
            raise_on_error=False,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Storage write failed"
        )

    row = FileMetadata(
        organisation_id=ctx.organisation_id,
        storage_key=key,
        storage_provider=backend.provider_name,
        original_filename=validated.filename,
        content_type=validated.content_type,
        size_bytes=validated.size_bytes,
        checksum_sha256=checksum,
        status="active",
        uploaded_by_user_id=ctx.user_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.FILE_UPLOAD,
        resource_type="file",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Private file uploaded",
        metadata={
            "content_type": validated.content_type,
            "size_bytes": validated.size_bytes,
            "resource_type": resource_type,
        },
    )
    return _public_view(row)


def get_active_file(
    session: Session, ctx: OrganisationContext, file_id: uuid.UUID
) -> FileMetadata:
    row = session.get(FileMetadata, file_id)
    if row is None or row.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    assert_same_organisation(ctx, row.organisation_id)
    return row


def get_file_metadata(
    session: Session, ctx: OrganisationContext, file_id: uuid.UUID
) -> dict[str, Any]:
    return _public_view(get_active_file(session, ctx, file_id))


def list_files(
    session: Session,
    ctx: OrganisationContext,
    *,
    page: int,
    page_size: int,
    resource_type: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    stmt = select(FileMetadata).where(
        FileMetadata.organisation_id == ctx.organisation_id,
        FileMetadata.status == "active",
    )
    if resource_type:
        stmt = stmt.where(FileMetadata.resource_type == resource_type)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset, limit = offset_limit(page, page_size)
    rows = list(
        session.scalars(
            stmt.order_by(FileMetadata.created_at.desc(), FileMetadata.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return [_public_view(row) for row in rows], total


def download_file(
    session: Session,
    ctx: OrganisationContext,
    file_id: uuid.UUID,
    *,
    backend: StorageBackend | None = None,
) -> tuple[FileMetadata, bytes]:
    backend = backend or get_storage_backend()
    row = get_active_file(session, ctx, file_id)
    try:
        data = backend.get_bytes(key=row.storage_key)
    except KeyError as exc:
        record_event(
            session,
            action=audit_events.FILE_DOWNLOAD_FAILURE,
            resource_type="file",
            resource_id=row.id,
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Object missing in storage",
            raise_on_error=False,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File content unavailable"
        ) from exc
    record_event(
        session,
        action=audit_events.FILE_DOWNLOAD,
        resource_type="file",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Private file downloaded",
        metadata={"size_bytes": row.size_bytes},
        raise_on_error=False,
    )
    return row, data


def delete_file(
    session: Session,
    ctx: OrganisationContext,
    file_id: uuid.UUID,
    *,
    backend: StorageBackend | None = None,
) -> dict[str, Any]:
    backend = backend or get_storage_backend()
    row = get_active_file(session, ctx, file_id)
    storage_key = row.storage_key
    now = datetime.now(timezone.utc)
    row.status = "deleted"
    row.deleted_at = now
    session.add(row)
    session.flush()
    try:
        backend.delete(key=storage_key)
    except Exception:
        logger.exception("Storage delete failed for file_id=%s", file_id)
        record_event(
            session,
            action=audit_events.FILE_DELETE_FAILURE,
            resource_type="file",
            resource_id=row.id,
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.FAILURE,
            summary="Metadata soft-deleted; object delete failed",
            raise_on_error=False,
        )
        # Metadata remains deleted so the file is not re-exposed; object may need GC.
    else:
        record_event(
            session,
            action=audit_events.FILE_DELETE,
            resource_type="file",
            resource_id=row.id,
            organisation_id=ctx.organisation_id,
            actor_user_id=ctx.user_id,
            actor_role=ctx.role.value,
            outcome=AuditOutcome.SUCCESS,
            summary="Private file soft-deleted",
        )
    return _public_view(row)
