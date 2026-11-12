"""Celery application for HMore background jobs (F2.2 reminders).

Organisation-safe job payloads must use app.tenancy.jobs.JobOrganisationContext
and validate_job_organisation_context before processing organisation data.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hmore",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_ignore_result=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "dispatch-due-reminders-every-minute": {
            "task": "hmore.reminders.dispatch_due",
            "schedule": 60.0,
        },
        "dispatch-complaint-overdue-escalations-every-15-minutes": {
            "task": "hmore.complaints.dispatch_overdue",
            "schedule": 900.0,
        },
        "scan-managed-document-expiry-reminders-hourly": {
            "task": "hmore.managed_documents.scan_expiry_reminders",
            "schedule": 3600.0,
        },
        "dispatch-f212-communication-reminders-every-minute": {
            "task": "hmore.communication.dispatch_scheduled_reminders",
            "schedule": 60.0,
        },
        "dispatch-pending-push-every-45-seconds": {
            "task": "hmore.push.dispatch_pending",
            "schedule": 45.0,
        },
        # F3.9 — daily compliance rules sweep (AI explains afterward inside the sweep)
        "dispatch-compliance-sweeps-daily": {
            "task": "hmore.compliance.dispatch_scheduled_sweeps",
            "schedule": 86400.0,
        },
        # F3.11 — daily search-based duplicate detection (no AI per record)
        "dispatch-duplicate-detection-daily": {
            "task": "hmore.duplicate_detection.dispatch_scheduled_sweeps",
            "schedule": 86400.0,
        },
        # F3.13 — overdue reminder scan (creates ReminderRecord rows; dispatch job delivers)
        "scan-overdue-reminders-hourly": {
            "task": "hmore.overdue_reminders.scan",
            "schedule": 3600.0,
        },
        # F3.13 — weekly/monthly report draft generation (idempotent per period)
        "dispatch-weekly-report-drafts": {
            "task": "hmore.report_drafts.dispatch_weekly",
            "schedule": 604800.0,
        },
        "dispatch-monthly-report-drafts": {
            "task": "hmore.report_drafts.dispatch_monthly",
            "schedule": 2592000.0,
        },
        # F6.2 — scheduled operational report delivery
        "dispatch-scheduled-reports-every-5-minutes": {
            "task": "hmore.reporting.dispatch_scheduled_reports",
            "schedule": 300.0,
        },
        # F6.2 — early-warning operational alerts (not F6.3 automation rules)
        "dispatch-early-warning-alerts-hourly": {
            "task": "hmore.reporting.dispatch_early_warning_alerts",
            "schedule": 3600.0,
        },
        # F6.3 — evaluate due automation rules (reminders / escalations / sweeps)
        "dispatch-automation-rules-every-5-minutes": {
            "task": "hmore.automation.dispatch_due_rules",
            "schedule": 300.0,
        },
        # F6.4 — optional auto health sync for connected integrations with config.auto_sync
        "dispatch-integration-auto-sync-hourly": {
            "task": "hmore.integrations.dispatch_auto_sync",
            "schedule": 3600.0,
        },
        # F6.5 — mark stale occupancy offline + apply count retention
        "dispatch-room-occupancy-sweep-every-5-minutes": {
            "task": "hmore.room_occupancy.sweep",
            "schedule": 300.0,
        },
    },
)

# Eagerly register reminder tasks for workers and unit tests.
import app.workers.tasks  # noqa: E402,F401
