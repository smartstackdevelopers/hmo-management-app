"""Celery app for AI service batch/scheduled workloads (F3.2).

Shares Redis with the core API broker URL convention but uses a distinct
Celery application name so task namespaces do not collide.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hmore-ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.batch.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        # Infrastructure heartbeat only — no tenant AI workloads in F3.2.
        "hmore-ai-foundation-ping-hourly": {
            "task": "hmore.ai.batch.scheduled_foundation_ping",
            "schedule": 3600.0,
            "options": {"expires": 3500},
        },
    },
)

# Register tasks for workers and unit discovery.
import app.batch.tasks  # noqa: E402,F401
