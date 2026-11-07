from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from app.batch.models import BatchJob, JobStatus
from app.context.trusted import TrustedCallerContext
from app.core.errors import ForbiddenError, ValidationServiceError, WorkflowError


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BatchJobStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, BatchJob] = {}
        self._idempotency: dict[tuple[str, str], str] = {}  # (org, key) -> job_id

    def create(
        self,
        *,
        ctx: TrustedCallerContext,
        workflow_id: str,
        idempotency_key: str | None,
        max_retries: int,
        metadata: dict | None = None,
    ) -> BatchJob:
        with self._lock:
            if idempotency_key:
                existing_id = self._idempotency.get((str(ctx.organisation_id), idempotency_key))
                if existing_id and existing_id in self._jobs:
                    return self._jobs[existing_id]
            job = BatchJob(
                job_id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                organisation_id=ctx.organisation_id,
                submitted_by_user_id=ctx.user_id,
                status=JobStatus.queued,
                created_at=_utcnow(),
                idempotency_key=idempotency_key,
                max_retries=max_retries,
                metadata=metadata or {},
            )
            self._jobs[job.job_id] = job
            if idempotency_key:
                self._idempotency[(str(ctx.organisation_id), idempotency_key)] = job.job_id
            return job

    def get(self, job_id: str, ctx: TrustedCallerContext) -> BatchJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise WorkflowError(f"Job '{job_id}' not found", status_code=404)
            if job.organisation_id != ctx.organisation_id:
                raise ForbiddenError("Job belongs to another organisation")
            return job

    def update(self, job: BatchJob) -> BatchJob:
        with self._lock:
            self._jobs[job.job_id] = job
            return job

    def mark_running(self, job_id: str) -> BatchJob:
        with self._lock:
            job = self._jobs[job_id]
            if job.status == JobStatus.cancelled:
                raise ValidationServiceError("Job was cancelled")
            updated = job.model_copy(
                update={"status": JobStatus.running, "started_at": _utcnow(), "attempt": job.attempt + 1}
            )
            self._jobs[job_id] = updated
            return updated

    def mark_completed(self, job_id: str, result_ref: dict) -> BatchJob:
        with self._lock:
            job = self._jobs[job_id]
            updated = job.model_copy(
                update={
                    "status": JobStatus.completed,
                    "finished_at": _utcnow(),
                    "result_ref": result_ref,
                    "error": None,
                }
            )
            self._jobs[job_id] = updated
            return updated

    def mark_failed(self, job_id: str, error: str, *, terminal: bool) -> BatchJob:
        with self._lock:
            job = self._jobs[job_id]
            status = JobStatus.failed if terminal else JobStatus.queued
            updated = job.model_copy(
                update={
                    "status": status,
                    "finished_at": _utcnow() if terminal else None,
                    "error": error,
                }
            )
            self._jobs[job_id] = updated
            return updated

    def cancel(self, job_id: str, ctx: TrustedCallerContext) -> BatchJob:
        with self._lock:
            job = self.get(job_id, ctx)
            if job.status in {JobStatus.completed, JobStatus.failed, JobStatus.cancelled}:
                raise ValidationServiceError(f"Cannot cancel job in status {job.status.value}")
            updated = job.model_copy(update={"status": JobStatus.cancelled, "finished_at": _utcnow()})
            self._jobs[job_id] = updated
            return updated


_STORE: BatchJobStore | None = None
_STORE_LOCK = threading.Lock()


def get_batch_store() -> BatchJobStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = BatchJobStore()
        return _STORE


def reset_batch_store_for_tests() -> BatchJobStore:
    global _STORE
    with _STORE_LOCK:
        _STORE = BatchJobStore()
        return _STORE
