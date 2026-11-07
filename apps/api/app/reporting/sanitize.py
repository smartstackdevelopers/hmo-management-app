"""CSV / spreadsheet formula-injection mitigation."""

from __future__ import annotations

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "|")


def sanitize_cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.startswith(FORMULA_PREFIXES):
        return "'" + text
    return text
