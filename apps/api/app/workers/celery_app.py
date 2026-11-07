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
    },
)

# Eagerly register reminder tasks for workers and unit tests.
import app.workers.tasks  # noqa: E402,F401
