"""Secure object-key generation. Never use client filenames as storage keys."""

from __future__ import annotations

import re
import uuid
from pathlib import PurePosixPath

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_ALLOWED_EXT = frozenset(
    {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".txt", ".doc", ".docx"}
)


def normalize_filename(filename: str | None) -> str:
    raw = (filename or "upload").strip().replace("\\", "/")
    name = PurePosixPath(raw).name
    if not name or name in {".", ".."}:
        name = "upload"
    name = _UNSAFE.sub("_", name)
    if len(name) > 200:
        stem = PurePosixPath(name).stem[:180]
        suffix = PurePosixPath(name).suffix[:20]
        name = f"{stem}{suffix}"
    return name


def extension_for(filename: str) -> str:
    suffix = PurePosixPath(normalize_filename(filename)).suffix.lower()
    if suffix in _ALLOWED_EXT:
        return suffix
    return ""


def build_object_key(*, organisation_id: uuid.UUID, original_filename: str) -> str:
    """Non-guessable key scoped under the organisation. Ignores path components."""
    safe_name = normalize_filename(original_filename)
    ext = extension_for(safe_name)
    token = uuid.uuid4().hex
    # Do not embed the original basename — only a random token + safe extension.
    return f"org/{organisation_id}/{token}{ext}"
