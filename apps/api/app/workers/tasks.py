"""Celery tasks for F2.2 reminders.

Run worker:
  celery -A app.workers.celery_app.celery_app worker -l info

Run beat (periodic dispatch):
  celery -A app.workers.celery_app.celery_app beat -l info
"""

from __future__ import annotations

import logging

from app.db.session import session_scope
from app.ops.reminders import dispatch_due_reminders, dispatch_org_reminders
from app.workers.celery_app import celery_app

logger = logging.getLogger("hmore.celery")


@celery_app.task(
    name="hmore.reminders.dispatch_due",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def dispatch_due_reminders_task(self) -> dict:
    """Periodic job: process due reminder_records across organisations."""
    with session_scope() as session:
        result = dispatch_due_reminders(session)
        logger.info("dispatch_due_reminders result=%s", result)
        return result


@celery_app.task(
    name="hmore.reminders.dispatch_organisation",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def dispatch_organisation_reminders_task(self, payload: dict) -> dict:
    """Organisation-scoped reminder dispatch with validated job context."""
    with session_scope() as session:
        result = dispatch_org_reminders(session, payload)
        logger.info("dispatch_org_reminders result=%s", result)
        return result
