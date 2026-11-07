from __future__ import annotations

from typing import Any, TypedDict


class BaseWorkflowState(TypedDict, total=False):
    organisation_id: str
    user_id: str
    role: str
    correlation_id: str
    prompt_id: str
    prompt_version: str
    rendered_prompt: str
    message: str
    tool_output: str
    llm_output: str | None
    requires_approval: bool
    approval_id: str | None
    proposed_action_summary: str | None
    error: str | None
    status: str
    extra: dict[str, Any]
