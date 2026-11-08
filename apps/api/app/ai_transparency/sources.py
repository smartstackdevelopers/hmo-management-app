"""Sanitize and preserve source references — never invent or reconstruct them."""

from __future__ import annotations

from typing import Any

_ALLOWED_KEYS = frozenset(
    {
        "type",
        "id",
        "title",
        "label",
        "document_ref",
        "version",
        "timestamp",
        "href",
        "location",
    }
)

_BLOCKED_KEYS = frozenset(
    {
        "prompt",
        "system_prompt",
        "content",
        "body",
        "raw",
        "embedding",
        "token",
        "api_key",
        "reasoning",
        "chain_of_thought",
        "cot",
    }
)


def sanitize_source_refs(raw: Any) -> list[dict[str, Any]]:
    """Convert workflow-provided refs into a safe list. Empty if nothing reliable."""
    items: list[Any]
    if raw is None:
        return []
    if isinstance(raw, dict):
        # Flatten dict-shaped refs (e.g. notes analysis) into one safe entry.
        if any(k in raw for k in ("type", "id", "daily_log_id", "tenant_id")):
            items = [raw]
        else:
            items = [{"type": k, "id": str(v)} for k, v in raw.items() if v is not None]
    elif isinstance(raw, list):
        items = raw
    else:
        return []

    out: list[dict[str, Any]] = []
    for item in items[:50]:
        if not isinstance(item, dict):
            continue
        cleaned: dict[str, Any] = {}
        for key, value in item.items():
            lk = str(key).lower()
            if lk in _BLOCKED_KEYS:
                continue
            if lk not in _ALLOWED_KEYS and lk not in {
                "daily_log_id",
                "source_note_version",
                "log_date",
                "tenant_id",
                "application_id",
                "document_id",
                "case_summary_id",
                "message_id",
                "content_id",
                "source_type",
                "version_token",
            }:
                continue
            if value is None:
                continue
            if isinstance(value, (str, int, bool)):
                cleaned[str(key)[:64]] = str(value)[:512] if isinstance(value, str) else value
            elif isinstance(value, float):
                continue
        # Normalise common id fields
        if "id" not in cleaned:
            for alt in (
                "daily_log_id",
                "tenant_id",
                "application_id",
                "document_id",
                "message_id",
                "content_id",
            ):
                if alt in cleaned:
                    cleaned["id"] = cleaned[alt]
                    cleaned.setdefault(
                        "type",
                        cleaned.get("source_type") or alt.replace("_id", ""),
                    )
                    break
        if cleaned.get("id") or cleaned.get("type") or cleaned.get("title") or cleaned.get("label"):
            out.append(cleaned)
    return out


def sources_available(refs: list[dict[str, Any]]) -> bool:
    return len(refs) > 0
