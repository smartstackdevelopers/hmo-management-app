"""F3.13 unit tests — periods and safety labels (no DB)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.report_drafts.periods import resolve_period
from app.report_drafts.service import NOTICE


def test_weekly_and_monthly_periods_are_ordered() -> None:
    anchor = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    weekly_start, weekly_end, tz = resolve_period("weekly", anchor=anchor)
    assert weekly_end > weekly_start
    assert tz == "Europe/London"
    monthly_start, monthly_end, _ = resolve_period("monthly", anchor=anchor)
    assert monthly_end > monthly_start


def test_draft_notice_requires_human_review() -> None:
    assert "AI-GENERATED DRAFT — REQUIRES HUMAN REVIEW" == NOTICE

