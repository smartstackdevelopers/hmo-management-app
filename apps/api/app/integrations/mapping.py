"""Field mapping validation and safe transformation foundation."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.integrations.constants import ALLOWED_DATA_TYPES


def validate_mapping_entries(entries: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise HTTPException(status_code=400, detail="mappings_json must be a list")
    cleaned: list[dict[str, Any]] = []
    seen_dest: set[str] = set()
    for idx, raw in enumerate(entries):
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail=f"mapping[{idx}] must be an object")
        source = str(raw.get("source_field") or "").strip()
        dest = str(raw.get("destination_field") or "").strip()
        dtype = str(raw.get("data_type") or "string").strip().lower()
        required = bool(raw.get("required", False))
        if not source or not dest:
            raise HTTPException(status_code=400, detail=f"mapping[{idx}] requires source_field and destination_field")
        if dtype not in ALLOWED_DATA_TYPES:
            raise HTTPException(status_code=400, detail=f"mapping[{idx}] has invalid data_type")
        if dest in seen_dest:
            raise HTTPException(status_code=400, detail=f"Duplicate destination_field: {dest}")
        seen_dest.add(dest)
        cleaned.append(
            {
                "source_field": source,
                "destination_field": dest,
                "data_type": dtype,
                "required": required,
            }
        )
    return cleaned


def _coerce(value: Any, data_type: str) -> Any:
    if value is None:
        return None
    if data_type == "string":
        return str(value)
    if data_type == "integer":
        return int(value)
    if data_type == "number":
        return float(value)
    if data_type == "boolean":
        if isinstance(value, bool):
            return value
        if str(value).lower() in {"1", "true", "yes"}:
            return True
        if str(value).lower() in {"0", "false", "no"}:
            return False
        raise ValueError("invalid boolean")
    if data_type == "date":
        if isinstance(value, date) and not isinstance(value, datetime):
            return value.isoformat()
        return date.fromisoformat(str(value)[:10]).isoformat()
    if data_type == "datetime":
        if isinstance(value, datetime):
            return value.isoformat()
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    if data_type == "uuid":
        return str(UUID(str(value)))
    return value


def apply_mapping(
    source: dict[str, Any],
    mappings: list[dict[str, Any]],
    *,
    allow_overwrite_keys: set[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Transform external/source payload using explicit mappings.

    Protected HMore keys cannot be overwritten unless listed in allow_overwrite_keys.
    """
    protected = {"id", "organisation_id", "role", "permissions", "password", "auth0_sub"}
    allow = allow_overwrite_keys or set()
    out: dict[str, Any] = {}
    errors: list[str] = []
    for entry in mappings:
        src = entry["source_field"]
        dest = entry["destination_field"]
        required = bool(entry.get("required"))
        dtype = entry.get("data_type") or "string"
        if dest in protected and dest not in allow:
            errors.append(f"Refusing to map into protected field '{dest}' without authorisation")
            continue
        if src not in source or source.get(src) is None:
            if required:
                errors.append(f"Missing required source field '{src}'")
            continue
        try:
            out[dest] = _coerce(source[src], dtype)
        except Exception as exc:  # noqa: BLE001 — collect mapping errors
            errors.append(f"Failed to coerce '{src}' -> '{dest}' as {dtype}: {exc}")
    return out, errors
