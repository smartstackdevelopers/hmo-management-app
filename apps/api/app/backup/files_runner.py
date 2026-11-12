"""Private file backup manifest — metadata only in default mode."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.file_metadata import FileMetadata


def write_files_manifest(session: Session, output_path: Path, organisation_id=None) -> dict[str, object]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stmt = select(FileMetadata).order_by(FileMetadata.created_at.desc())
    if organisation_id is not None:
        stmt = stmt.where(FileMetadata.organisation_id == organisation_id)
    rows = session.scalars(stmt.limit(10_000)).all()
    items = [
        {
            "id": str(row.id),
            "organisation_id": str(row.organisation_id),
            "storage_key": row.storage_key,
            "content_type": row.content_type,
            "size_bytes": row.size_bytes,
            "checksum_sha256": row.checksum_sha256,
        }
        for row in rows
    ]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(items),
        "items": items,
        "note": "Manifest only — binary objects copied separately in operator S3 replication",
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
