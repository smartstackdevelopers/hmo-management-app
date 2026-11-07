from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ProposedAction(BaseModel):
    """AI suggestion that must not mutate business records until explicitly approved."""

    action_type: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    organisation_id: UUID
    proposed_by_workflow: str
    created_at: datetime
    source: str = "ai_suggestion"  # never "human_approval"


class ApprovalRecord(BaseModel):
    approval_id: str
    status: ApprovalStatus
    proposed_action: ProposedAction
    reviewer_user_id: UUID | None = None
    decision_note: str | None = None
    decided_at: datetime | None = None

    @property
    def is_human_approved(self) -> bool:
        return self.status == ApprovalStatus.approved and self.reviewer_user_id is not None
