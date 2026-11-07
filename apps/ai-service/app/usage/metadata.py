from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class UsageMetadata:
    """Usage capture for F3.3 — no invented monetary costs."""

    request_id: str
    correlation_id: str
    workflow_id: str
    organisation_id: UUID
    user_id: UUID
    prompt_id: str | None = None
    prompt_version: str | None = None
    provider: str | None = None
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cache_hit: bool | None = None
    escalation_occurred: bool | None = None
    escalation_reason: str | None = None
    batch_job_id: str | None = None
    status: str = "started"
    duration_ms: int | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    monetary_cost: None = None

    def to_public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["organisation_id"] = str(self.organisation_id)
        data["user_id"] = str(self.user_id)
        data["timestamp"] = self.timestamp.isoformat()
        data["monetary_cost"] = None
        return data
