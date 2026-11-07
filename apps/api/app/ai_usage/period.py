"""Calendar-month budget period helpers (F3.3)."""

from __future__ import annotations

from datetime import date, datetime, timezone


def period_key_for(when: date | datetime | None = None) -> str:
    """Return YYYY-MM for the UTC calendar month of `when` (default: now UTC)."""
    if when is None:
        when = datetime.now(timezone.utc)
    if isinstance(when, datetime):
        when = when.astimezone(timezone.utc).date()
    return f"{when.year:04d}-{when.month:02d}"


def previous_period_key(period_key: str) -> str:
    year = int(period_key[:4])
    month = int(period_key[5:7])
    if month == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month - 1:02d}"
