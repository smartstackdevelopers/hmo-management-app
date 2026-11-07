from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class BatchJob(BaseModel):
    job_id: str
    workflow_id: str
    organisation_id: UUID
    submitted_by_user_id: UUID
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    idempotency_key: str | None = None
    attempt: int = 0
    max_retries: int = 2
    error: str | None = None
    result_ref: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
