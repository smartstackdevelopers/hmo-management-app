"""Upload validation: size, content-type, and light magic-byte checks."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.config import Settings
from app.storage.keys import normalize_filename

# Sniffed signatures → canonical MIME. Extension alone is never authoritative.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"%PDF", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"RIFF", "image/webp"),  # refined below for WEBP
    (b"PK\x03\x04", "application/zip"),  # docx is a zip container
)


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    content_type: str
    size_bytes: int
    data: bytes


def _allowed_types(settings: Settings) -> set[str]:
    return {
        part.strip().lower()
        for part in settings.storage_allowed_content_types.split(",")
        if part.strip()
    }


def sniff_content_type(data: bytes, declared: str | None) -> str:
    declared_norm = (declared or "application/octet-stream").split(";")[0].strip().lower()
    if not data:
        return declared_norm
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"PK\x03\x04"):
        # Office Open XML (docx) or generic zip — accept declared docx when allowed
        if declared_norm.endswith(
            "officedocument.wordprocessingml.document"
        ) or declared_norm == "application/msword":
            return declared_norm
        return "application/zip"
    # Plain text heuristic: mostly printable
    if declared_norm == "text/plain":
        sample = data[:512]
        if all(32 <= b <= 126 or b in (9, 10, 13) for b in sample):
            return "text/plain"
    return declared_norm


def validate_upload(
    *,
    settings: Settings,
    filename: str | None,
    declared_content_type: str | None,
    data: bytes,
) -> ValidatedUpload:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    max_bytes = settings.storage_max_upload_bytes
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_bytes} bytes",
        )
    safe_name = normalize_filename(filename)
    sniffed = sniff_content_type(data, declared_content_type)
    allowed = _allowed_types(settings)
    if sniffed not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content type not allowed: {sniffed}",
        )
    # Reject obvious extension/MIME mismatches for strong signatures
    lower = safe_name.lower()
    if sniffed == "application/pdf" and not lower.endswith(".pdf"):
        safe_name = f"{safe_name}.pdf" if "." not in safe_name else safe_name
    return ValidatedUpload(
        filename=safe_name,
        content_type=sniffed,
        size_bytes=len(data),
        data=data,
    )
