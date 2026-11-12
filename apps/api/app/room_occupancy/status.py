"""Occupancy status calculation — five required statuses only."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def compute_occupancy_status(
    *,
    estimated_count: int | None,
    max_capacity: int,
    near_capacity_percent: int,
    last_count_at: datetime | None,
    offline_after_seconds: int,
    device_online: bool,
    now: datetime | None = None,
) -> tuple[str, int | None]:
    """Return (status, occupancy_percent). Offline never shown as zero occupants."""
    now = now or datetime.now(timezone.utc)
    capacity = max(1, int(max_capacity or 1))
    threshold = max(1, min(100, int(near_capacity_percent or 80)))

    if not device_online:
        return "offline", None
    if last_count_at is None:
        return "offline", None
    age = now - (last_count_at if last_count_at.tzinfo else last_count_at.replace(tzinfo=timezone.utc))
    if age > timedelta(seconds=max(30, offline_after_seconds)):
        return "offline", None
    if estimated_count is None:
        return "offline", None

    count = max(0, int(estimated_count))
    percent = int(round((count / capacity) * 100))
    if count <= 0:
        return "available", 0
    if count >= capacity:
        return "at_capacity", min(percent, 100) if percent else 100
    if percent >= threshold:
        return "near_capacity", percent
    return "occupied", percent
