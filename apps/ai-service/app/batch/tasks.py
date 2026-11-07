from __future__ import annotations

import logging
import uuid
from typing import Any

from app.batch.celery_app import celery_app
from app.batch.store import get_batch_store
from app.context.trusted import TrustedCallerContext
from app.core.config import get_settings
from app.graph.runtime import execute_workflow

logger = logging.getLogger("hmore.ai.batch")


def _ctx_from_payload(payload: dict[str, Any]) -> TrustedCallerContext:
    return TrustedCallerContext(
        organisation_id=uuid.UUID(payload["organisation_id"]),
        user_id=uuid.UUID(payload["user_id"]),
        role=payload["role"],
        features=frozenset(payload.get("features") or []),
    )


@celery_app.task(
    name="hmore.ai.batch.execute_workflow",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    autoretry_for=(),
)
def execute_workflow_job(self, job_id: str, trusted_payload: dict[str, Any], message: str = "") -> dict[str, Any]:
    """Execute an allow-listed workflow for a previously submitted job.

    Organisation context comes only from trusted_payload captured at submission.
    """
    store = get_batch_store()
    settings = get_settings()
    try:
        job = store.mark_running(job_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("job_not_runnable job_id=%s error=%s", job_id, type(exc).__name__)
        return {"status": "skipped", "reason": type(exc).__name__}

    ctx = _ctx_from_payload(trusted_payload)
    if job.organisation_id != ctx.organisation_id:
        store.mark_failed(job_id, "organisation context mismatch", terminal=True)
        return {"status": "failed", "error": "organisation_mismatch"}

    try:
        result = execute_workflow(
            workflow_id=job.workflow_id,
            ctx=ctx,
            settings=settings,
            message=message,
            require_human_gate=False,
            batch_job_id=job_id,
        )
        # Persist a reference only — avoid dumping sensitive prompt content.
        ref = {
            "request_id": result.get("request_id"),
            "status": result.get("status"),
            "workflow_id": result.get("workflow_id"),
        }
        store.mark_completed(job_id, ref)
        return {"status": "completed", "result_ref": ref}
    except Exception as exc:  # noqa: BLE001
        transient = type(exc).__name__ in {"ProviderError", "TimeoutError", "ConnectionError"}
        terminal = (not transient) or job.attempt >= job.max_retries
        store.mark_failed(job_id, type(exc).__name__, terminal=terminal)
        if not terminal:
            raise self.retry(exc=exc)
        return {"status": "failed", "error": type(exc).__name__}


@celery_app.task(name="hmore.ai.batch.scheduled_foundation_ping")
def scheduled_foundation_ping() -> dict[str, str]:
    """Scheduled infrastructure check — does not touch tenant data."""
    from app.graph.foundation import ping_graph

    return {"status": "ok", "graph": ping_graph()}
