"""Safe normalisation helpers for F3.11 duplicate detection."""

from __future__ import annotations

import re
import unicodedata

_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_PHONE_DIGITS = re.compile(r"\D+")


def collapse_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _WS.sub(" ", value.strip())
    return cleaned or None


def lower_text(value: str | None) -> str | None:
    cleaned = collapse_whitespace(value)
    return cleaned.lower() if cleaned else None


def normalize_name(value: str | None) -> str | None:
    cleaned = lower_text(value)
    if cleaned is None:
        return None
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = _NON_ALNUM.sub(" ", cleaned)
    cleaned = _WS.sub(" ", cleaned).strip()
    return cleaned or None


def normalize_email(value: str | None) -> str | None:
    cleaned = lower_text(value)
    return cleaned or None


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    digits = _PHONE_DIGITS.sub("", value)
    if len(digits) < 7:
        return None
    # Keep meaningful leading zeros; do not strip country codes aggressively.
    return digits


def normalize_reference(value: str | None) -> str | None:
    cleaned = lower_text(value)
    if cleaned is None:
        return None
    return _NON_ALNUM.sub("", cleaned) or None


def name_prefix(value: str | None, size: int = 3) -> str | None:
    normalized = normalize_name(value)
    if not normalized:
        return None
    compact = normalized.replace(" ", "")
    return compact[:size] if compact else None
