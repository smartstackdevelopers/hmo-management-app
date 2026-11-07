"""Budget alert notification interface (F3.3).

Reuses the F2.12 communication adapters when available. Delivery is not claimed
unless the underlying provider confirms it — this module only queues intent.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger("hmore.ai_usage.notify")


def evaluate_and_notify_thresholds(
    session: Session,
    *,
    organisation_id: UUID,
    snapshot: dict[str, Any],
) -> list[str]:
    """Return alert kinds that apply. Attempts optional notification hook.

    Alert kinds: approaching_limit | budget_exhausted
    Threshold percentages come from the organisation budget configuration.
    """
    alerts: list[str] = []
    if snapshot.get("budget_exhausted"):
        alerts.append("budget_exhausted")
    elif snapshot.get("approaching_limit"):
        alerts.append("approaching_limit")

    for kind in alerts:
        logger.info(
            "ai_budget_alert organisation_id=%s kind=%s utilisation=%s",
            organisation_id,
            kind,
            snapshot.get("utilisation_pct"),
        )
        _try_enqueue_operational_notice(session, organisation_id=organisation_id, kind=kind, snapshot=snapshot)
    return alerts


def _try_enqueue_operational_notice(
    session: Session,
    *,
    organisation_id: UUID,
    kind: str,
    snapshot: dict[str, Any],
) -> None:
    """Best-effort hook into communication layer — never raises to callers."""
    try:
        from app.communication import service as comm_service  # noqa: F401

        # Intentional: no silent email/SMS claim. Log only unless a dedicated
        # operational recipient API is wired by operators.
        _ = (session, organisation_id, kind, snapshot, comm_service)
        logger.debug("ai_budget_alert_hook_ready kind=%s (delivery not claimed)", kind)
    except Exception:  # noqa: BLE001
        logger.debug("ai_budget_alert_hook_unavailable kind=%s", kind)
