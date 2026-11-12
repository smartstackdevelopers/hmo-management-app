"""Celery tasks for F2.2 reminders.

Run worker:
  celery -A app.workers.celery_app.celery_app worker -l info

Run beat (periodic dispatch):
  celery -A app.workers.celery_app.celery_app beat -l info
"""

from __future__ import annotations

import logging
import uuid

from app.db.session import session_scope
from app.communication.jobs import dispatch_due_communication_reminders
from app.managed_documents.jobs import scan_and_schedule_document_reminders
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


@celery_app.task(
    name="hmore.complaints.dispatch_overdue",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def dispatch_complaint_overdue_task(self) -> dict:
    """Periodic job: escalate overdue complaints using operational deadline rules."""
    from app.complaints.jobs import dispatch_overdue_escalations

    with session_scope() as session:
        result = dispatch_overdue_escalations(session)
        logger.info("dispatch_overdue_escalations result=%s", result)
        return result


@celery_app.task(
    name="hmore.complaints.dispatch_organisation_overdue",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def dispatch_org_complaint_overdue_task(self, payload: dict) -> dict:
    """Organisation-scoped overdue complaint escalation with validated job context."""
    from app.complaints.jobs import dispatch_org_overdue_escalations

    with session_scope() as session:
        result = dispatch_org_overdue_escalations(session, payload)
        logger.info("dispatch_org_overdue_escalations result=%s", result)
        return result


@celery_app.task(
    name="hmore.managed_documents.scan_expiry_reminders",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def scan_managed_document_expiry_reminders_task(self) -> dict:
    """Periodic: enqueue idempotent ReminderRecord rows for document expiry windows."""
    with session_scope() as session:
        result = scan_and_schedule_document_reminders(session)
        session.commit()
        logger.info("scan_managed_document_expiry_reminders result=%s", result)
        return result


@celery_app.task(
    name="hmore.communication.dispatch_scheduled_reminders",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def dispatch_communication_reminders_task(self) -> dict:
    """Periodic: dispatch due communication_scheduled_reminders (F2.12)."""
    with session_scope() as session:
        result = dispatch_due_communication_reminders(session)
        session.commit()
        logger.info("dispatch_due_communication_reminders result=%s", result)
        return result


@celery_app.task(
    name="hmore.compliance.dispatch_scheduled_sweeps",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def dispatch_compliance_sweeps_task(self) -> dict:
    """Periodic: organisation-scoped F3.9 compliance rules sweeps."""
    from app.compliance_agent.jobs import dispatch_scheduled_sweeps

    with session_scope() as session:
        result = dispatch_scheduled_sweeps(session)
        logger.info("dispatch_scheduled_compliance_sweeps result=%s", result)
        return result


@celery_app.task(
    name="hmore.compliance.dispatch_organisation_sweep",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def dispatch_org_compliance_sweep_task(self, payload: dict) -> dict:
    """Organisation-scoped compliance sweep with validated job context."""
    from app.compliance_agent.jobs import dispatch_org_scheduled_sweep

    with session_scope() as session:
        result = dispatch_org_scheduled_sweep(session, payload)
        logger.info("dispatch_org_compliance_sweep result=%s", result)
        return result


@celery_app.task(
    name="hmore.duplicate_detection.dispatch_scheduled_sweeps",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def dispatch_scheduled_duplicate_detection_task(self) -> dict:
    """Daily org-scoped duplicate detection sweeps (search-based; no AI)."""
    from app.duplicate_detection.jobs import dispatch_scheduled_sweeps

    with session_scope() as session:
        result = dispatch_scheduled_sweeps(session)
        logger.info("dispatch_scheduled_duplicate_detection result=%s", result)
        return result


@celery_app.task(
    name="hmore.duplicate_detection.dispatch_organisation_sweep",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def dispatch_org_duplicate_detection_task(self, payload: dict) -> dict:
    """Organisation-scoped duplicate detection sweep with validated job context."""
    from app.duplicate_detection.jobs import dispatch_org_scheduled_sweep

    with session_scope() as session:
        result = dispatch_org_scheduled_sweep(session, payload)
        logger.info("dispatch_org_duplicate_detection result=%s", result)
        return result


@celery_app.task(
    name="hmore.overdue_reminders.scan",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def scan_overdue_reminders_task(self) -> dict:
    """Scan overdue tasks/follow-ups/safeguarding and upsert ReminderRecord rows."""
    from app.report_drafts.overdue import dispatch_overdue_scans

    with session_scope() as session:
        result = dispatch_overdue_scans(session)
        logger.info("scan_overdue_reminders result=%s", result)
        return result


@celery_app.task(
    name="hmore.report_drafts.dispatch_weekly",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def dispatch_weekly_report_drafts_task(self) -> dict:
    from app.report_drafts.jobs import dispatch_period_drafts

    with session_scope() as session:
        result = dispatch_period_drafts(session, "weekly")
        logger.info("dispatch_weekly_report_drafts result=%s", result)
        return result


@celery_app.task(
    name="hmore.report_drafts.dispatch_monthly",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def dispatch_monthly_report_drafts_task(self) -> dict:
    from app.report_drafts.jobs import dispatch_period_drafts

    with session_scope() as session:
        result = dispatch_period_drafts(session, "monthly")
        logger.info("dispatch_monthly_report_drafts result=%s", result)
        return result


@celery_app.task(name="hmore.push.dispatch_delivery")
def dispatch_push_delivery_task(delivery_id: str) -> dict:
    """Send one queued push delivery. No-op when it is already sent or failed."""
    from app.push.delivery import dispatch_delivery_by_id

    with session_scope() as session:
        result = dispatch_delivery_by_id(session, uuid.UUID(str(delivery_id)))
        logger.info("dispatch_push_delivery result=%s", result)
        return result


@celery_app.task(name="hmore.push.dispatch_pending")
def dispatch_pending_push_task() -> dict:
    """Beat sweep for push deliveries still queued."""
    from app.push.delivery import dispatch_pending

    with session_scope() as session:
        result = dispatch_pending(session)
        logger.info("dispatch_pending_push result=%s", result)
        return result


@celery_app.task(
    name="hmore.reporting.dispatch_scheduled_reports",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def dispatch_scheduled_reports_task(self) -> dict:
    """F6.2: generate due scheduled reports and notify authorised recipients."""
    from app.reporting.jobs import dispatch_due_scheduled_reports

    with session_scope() as session:
        result = dispatch_due_scheduled_reports(session)
        logger.info("dispatch_scheduled_reports result=%s", result)
        return result


@celery_app.task(
    name="hmore.reporting.dispatch_early_warning_alerts",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def dispatch_early_warning_alerts_task(self) -> dict:
    """F6.2: evaluate early-warning thresholds from live operational data."""
    from app.reporting.jobs import dispatch_early_warning_scan

    with session_scope() as session:
        result = dispatch_early_warning_scan(session)
        logger.info("dispatch_early_warning_alerts result=%s", result)
        return result


@celery_app.task(
    name="hmore.automation.dispatch_due_rules",
    bind=True,
    soft_time_limit=240,
    time_limit=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def dispatch_due_automation_rules_task(self) -> dict:
    """F6.3: evaluate due automation rules; isolate per-rule failures."""
    from app.automation.jobs import dispatch_due_automation_rules

    with session_scope() as session:
        result = dispatch_due_automation_rules(session)
        logger.info("dispatch_due_automation_rules result=%s", result)
        return result


@celery_app.task(
    name="hmore.automation.retry_failed_run",
    bind=True,
    soft_time_limit=120,
    time_limit=180,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def retry_failed_automation_run_task(self, run_id: str) -> dict:
    """F6.3: safely retry a failed automation run."""
    from app.automation.jobs import retry_failed_run

    with session_scope() as session:
        result = retry_failed_run(session, uuid.UUID(str(run_id)))
        logger.info("retry_failed_automation_run result=%s", result)
        return result


@celery_app.task(
    name="hmore.integrations.dispatch_auto_sync",
    bind=True,
    soft_time_limit=240,
    time_limit=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def dispatch_integration_auto_sync_task(self) -> dict:
    """F6.4: hourly health sync for connected integrations with auto_sync enabled."""
    from app.integrations.sync import dispatch_due_scheduled_syncs

    with session_scope() as session:
        result = dispatch_due_scheduled_syncs(session)
        logger.info("dispatch_integration_auto_sync result=%s", result)
        return result
