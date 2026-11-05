"""Celery application stub.

Organisation-safe job payloads must use app.tenancy.jobs.JobOrganisationContext
and validate_job_organisation_context before processing organisation data (F1.5).
Full workflow automation is out of scope for F1.5.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hmore",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(task_ignore_result=True, task_serializer="json")
