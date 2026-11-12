"""F6.8 / Phase 6 integration — Celery beat registration smoke checks.

Ensures Phase 6 scheduled jobs are registered so workers can run without a browser.
Does not execute Redis/Celery at runtime (no broker required).
"""

from __future__ import annotations

from app.workers.celery_app import celery_app


REQUIRED_PHASE6_BEAT = {
    "dispatch-scheduled-reports-every-5-minutes": "hmore.reporting.dispatch_scheduled_reports",
    "dispatch-early-warning-alerts-hourly": "hmore.reporting.dispatch_early_warning_alerts",
    "dispatch-automation-rules-every-5-minutes": "hmore.automation.dispatch_due_rules",
    "dispatch-integration-auto-sync-hourly": "hmore.integrations.dispatch_auto_sync",
    "dispatch-room-occupancy-sweep-every-5-minutes": "hmore.room_occupancy.sweep",
}


def test_phase6_celery_beat_tasks_registered() -> None:
    schedule = celery_app.conf.beat_schedule
    for key, task_name in REQUIRED_PHASE6_BEAT.items():
        assert key in schedule, f"Missing beat entry: {key}"
        assert schedule[key]["task"] == task_name
        assert float(schedule[key]["schedule"]) > 0
