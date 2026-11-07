from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class WorkflowExecuteRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(default="", max_length=4000)
    require_human_gate: bool = False
    quality_requirement: str | None = Field(default=None, max_length=20)
    # Intentionally ignored for authz — present only so tests can prove rejection.
    organisation_id: UUID | None = None
    # Workflow-specific payload (for example notes_analysis.note). Not used for authorisation.
    input_payload: dict[str, Any] | None = None

    @field_validator("workflow_id")
    @classmethod
    def _strip_workflow(cls, value: str) -> str:
        return value.strip()


class WorkflowExecuteResponse(BaseModel):
    workflow_id: str
    status: str
    request_id: str
    organisation_id: str
    result: dict[str, Any]
    requires_approval: bool = False
    approval_id: str | None = None
    proposed_action_summary: str | None = None
    usage: dict[str, Any]


class ApprovalDecisionRequest(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=1000)


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    status: str
    reviewer_user_id: str | None
    is_human_approved: bool
    proposed_action_source: str


class PromptListResponse(BaseModel):
    items: list[dict[str, Any]]


class ProviderStatusResponse(BaseModel):
    configured_provider: str
    available: bool
    detail: str


class BatchSubmitRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(default="", max_length=4000)
    idempotency_key: str | None = Field(default=None, max_length=120)
    organisation_id: UUID | None = None


class BatchJobResponse(BaseModel):
    job_id: str
    workflow_id: str
    organisation_id: str
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    attempt: int = 0
    error: str | None = None
    result_ref: dict[str, Any] | None = None
    idempotency_key: str | None = None
