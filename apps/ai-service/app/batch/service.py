from __future__ import annotations

from typing import Any

from app.batch.models import BatchJob
from app.batch.store import get_batch_store
from app.context.trusted import TrustedCallerContext
from app.core.config import Settings
from app.core.errors import WorkflowError
from app.graph.runtime import SUPPORTED_WORKFLOWS


def submit_batch_job(
    *,
    ctx: TrustedCallerContext,
    settings: Settings,
    workflow_id: str,
    message: str = "",
    idempotency_key: str | None = None,
    enqueue: bool = True,
) -> BatchJob:
    if workflow_id not in SUPPORTED_WORKFLOWS:
        raise WorkflowError(f"Unsupported workflow '{workflow_id}'", status_code=404)
    store = get_batch_store()
    job = store.create(
        ctx=ctx,
        workflow_id=workflow_id,
        idempotency_key=idempotency_key,
        max_retries=settings.ai_batch_max_retries,
        metadata={"message_len": len(message)},
    )
    if enqueue and settings.ai_batch_eager:
        # Deterministic local/test path without a live worker.
        from app.batch.tasks import execute_workflow_job

        trusted = {
            "organisation_id": str(ctx.organisation_id),
            "user_id": str(ctx.user_id),
            "role": ctx.role,
            "features": sorted(ctx.features),
        }
        execute_workflow_job(job.job_id, trusted, message=message)
        return store.get(job.job_id, ctx)

    if enqueue:
        from app.batch.tasks import execute_workflow_job

        trusted = {
            "organisation_id": str(ctx.organisation_id),
            "user_id": str(ctx.user_id),
            "role": ctx.role,
            "features": sorted(ctx.features),
        }
        try:
            execute_workflow_job.delay(job.job_id, trusted, message=message)
        except Exception as exc:  # noqa: BLE001
            if settings.ai_batch_fail_open_to_eager:
                execute_workflow_job(job.job_id, trusted, message=message)
                return store.get(job.job_id, ctx)
            store.mark_failed(job.job_id, f"enqueue_failed:{type(exc).__name__}", terminal=True)
            raise WorkflowError("Failed to enqueue batch job", status_code=503) from exc
    return job


def job_to_public(job: BatchJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "workflow_id": job.workflow_id,
        "organisation_id": str(job.organisation_id),
        "status": job.status.value,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "attempt": job.attempt,
        "error": job.error,
        "result_ref": job.result_ref,
        "idempotency_key": job.idempotency_key,
    }
