"""Celery-backed automation rule evaluation (F6.3)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automation.engine import execute_rule
from app.db.models.automation import AutomationRule, AutomationRuleRun
from app.db.models.organisation import Organisation

logger = logging.getLogger("hmore.automation.jobs")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def dispatch_due_automation_rules(session: Session) -> dict[str, Any]:
    """Evaluate enabled rules that are due. Failures are isolated per rule."""
    now = _now()
    due = session.scalars(
        select(AutomationRule).where(
            AutomationRule.is_enabled.is_(True),
            AutomationRule.frequency != "manual",
            AutomationRule.next_run_at.is_not(None),
            AutomationRule.next_run_at <= now,
        )
    ).all()
    results: list[dict[str, Any]] = []
    for rule in due:
        try:
            results.append(execute_rule(session, rule.id))
        except Exception as exc:  # noqa: BLE001 — never stop the batch
            logger.exception("Automation dispatch failed for rule %s", rule.id)
            results.append({"ok": False, "rule_id": str(rule.id), "error": str(exc)[:500]})
    return {"processed": len(results), "results": results}


def dispatch_org_automation_rules(session: Session, organisation_id: uuid.UUID) -> dict[str, Any]:
    rules = session.scalars(
        select(AutomationRule).where(
            AutomationRule.organisation_id == organisation_id,
            AutomationRule.is_enabled.is_(True),
            AutomationRule.frequency != "manual",
        )
    ).all()
    results = []
    for rule in rules:
        try:
            results.append(execute_rule(session, rule.id, force=True))
        except Exception as exc:  # noqa: BLE001
            results.append({"ok": False, "rule_id": str(rule.id), "error": str(exc)[:500]})
    return {"organisation_id": str(organisation_id), "processed": len(results), "results": results}


def retry_failed_run(session: Session, run_id: uuid.UUID) -> dict[str, Any]:
    run = session.get(AutomationRuleRun, run_id)
    if run is None:
        return {"ok": False, "error": "run_not_found"}
    if run.status != "failed":
        return {"ok": False, "error": "not_failed"}
    return execute_rule(session, run.rule_id, retry_run_id=run.id)


def list_org_ids(session: Session) -> list[uuid.UUID]:
    return list(session.scalars(select(Organisation.id)).all())
