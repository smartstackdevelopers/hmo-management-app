"""Reporting period helpers. Organisation has no timezone column yet — Europe/London default."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Europe/London"


def resolve_period(
    period_type: str,
    *,
    anchor: datetime | None = None,
    timezone_name: str = DEFAULT_TZ,
) -> tuple[datetime, datetime, str]:
    if period_type not in {"weekly", "monthly"}:
        raise ValueError("period_type must be weekly or monthly")
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:  # noqa: BLE001
        tz = ZoneInfo(DEFAULT_TZ)
        timezone_name = DEFAULT_TZ
    now_local = (anchor or datetime.now(timezone.utc)).astimezone(tz)
    if period_type == "weekly":
        # Previous complete Mon–Sun week ending before today.
        start_of_week = (now_local - timedelta(days=now_local.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        period_start = start_of_week - timedelta(days=7)
        period_end = start_of_week
    else:
        first_this_month = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = first_this_month
        period_start = (first_this_month - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return period_start.astimezone(timezone.utc), period_end.astimezone(timezone.utc), timezone_name
