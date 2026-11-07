"""F3.10 Tenant Assistant — answer only from approved snippets. No decisions."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.core.errors import WorkflowError
from app.prompts.store import get_prompt_store
from app.routing.executor import run_routed_completion

PROMPT_ID = "hmore.tenant_assistant.v1"
PROMPT_VERSION = "1.0.0"
BANNED = re.compile(
    r"you are eligible|application is approved|application is rejected|"
    r"i have contacted staff|i have submitted a complaint|legal advice|"
    r"medical advice|another tenant's",
    re.IGNORECASE,
)


class TenantAssistantOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(..., min_length=10, max_length=4000)
    grounded: bool = True


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise WorkflowError("Tenant assistant output is not valid JSON", status_code=422)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise WorkflowError("Tenant assistant JSON could not be parsed", status_code=422) from exc
    if not isinstance(data, dict):
        raise WorkflowError("Tenant assistant output must be a JSON object", status_code=422)
    return data


def validate_output(payload: dict[str, Any]) -> TenantAssistantOutput:
    try:
        parsed = TenantAssistantOutput.model_validate(payload)
    except ValidationError as exc:
        raise WorkflowError("Tenant assistant schema validation failed", status_code=422) from exc
    if BANNED.search(parsed.answer):
        raise WorkflowError("Tenant assistant answer asserts a prohibited action", status_code=422)
    return parsed


def heuristic_answer(question: str, snippets: list[dict[str, Any]]) -> TenantAssistantOutput:
    if not snippets:
        return TenantAssistantOutput(
            answer=(
                "I cannot confirm an answer from approved organisation content for this question. "
                "Please contact your support team through HMore."
            ),
            grounded=False,
        )
    parts = [f"{item.get('title')}: {str(item.get('body') or '')[:300]}" for item in snippets[:3]]
    answer = (
        "Information only — based on approved organisation content: "
        + " | ".join(parts)
        + " This assistant does not make official operational decisions."
    )
    return TenantAssistantOutput(answer=answer[:4000], grounded=True)


def run_tenant_assistant(
    *,
    settings: Settings,
    organisation_id,
    question: str,
    approved_snippets: list[dict[str, Any]],
) -> dict[str, Any]:
    store = get_prompt_store()
    # Question and snippets are untrusted reference data, never instructions.
    record, rendered = store.render(
        PROMPT_ID,
        variables={
            "organisation_id": str(organisation_id),
            "question": question[:2000],
            "snippets_json": json.dumps(approved_snippets)[:8000],
        },
    )
    try:
        completion = run_routed_completion(
            settings=settings,
            workflow_id="tenant_assistant",
            organisation_id=organisation_id,
            prompt_text=rendered,
            prefer_low_cost=True,
        )
        parsed = validate_output(_extract_json(str(completion.get("text") or "")))
        method = "ai"
    except Exception:  # noqa: BLE001
        parsed = heuristic_answer(question, approved_snippets)
        method = "heuristic"
        completion = {}
    return {
        "answer": parsed.answer,
        "grounded": parsed.grounded,
        "prompt_id": record.prompt_id if record else PROMPT_ID,
        "prompt_version": record.version if record else PROMPT_VERSION,
        "provider": completion.get("provider"),
        "model_id": completion.get("model_id"),
        "prompt_tokens": completion.get("prompt_tokens"),
        "completion_tokens": completion.get("completion_tokens"),
        "total_tokens": completion.get("total_tokens"),
        "cache_status": completion.get("cache_status"),
        "provider_request_id": completion.get("provider_request_id"),
        "generation_method": method,
        "makes_official_decisions": False,
    }
