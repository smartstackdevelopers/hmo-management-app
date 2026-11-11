"""F5.4 optional explanation of a retrieved job match.

Uses only supplied job and profile facts. Never invents vacancies or salaries.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.core.errors import WorkflowError
from app.prompts.store import get_prompt_store
from app.routing.executor import run_routed_completion

PROMPT_ID = "hmore.job_match_explain.v1"
PROMPT_VERSION = "1.0.0"


class JobMatchExplainOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    explanation: str = Field(..., min_length=1, max_length=4000)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise WorkflowError("Job match explain output is not valid JSON", status_code=422)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise WorkflowError("Job match explain output JSON could not be parsed", status_code=422) from exc
    if not isinstance(data, dict):
        raise WorkflowError("Job match explain output must be a JSON object", status_code=422)
    return data


def run_job_match_explain(
    *,
    settings: Settings,
    organisation_id,
    job: dict[str, Any],
    profile_summary: dict[str, Any],
    match: dict[str, Any],
    question: str | None = None,
) -> dict[str, Any]:
    if settings.llm_provider not in {"openai", "mock"}:
        raise WorkflowError(
            "AI job match explanation is unavailable because no language model is configured",
            status_code=503,
        )
    store = get_prompt_store()
    record, rendered = store.render(
        PROMPT_ID,
        variables={"organisation_id": str(organisation_id)},
    )
    user_message = json.dumps(
        {
            "job": job,
            "profile_summary": profile_summary,
            "match": match,
            "question": question,
            "output_schema": {"explanation": "string"},
        },
        ensure_ascii=True,
    )
    routed = run_routed_completion(
        settings=settings,
        organisation_id=organisation_id,
        workflow_id="job_match_explain",
        prompt_id=record.prompt_id,
        prompt_version=record.version,
        rendered_prompt=rendered,
        user_message=user_message,
        quality_requirement="standard",
        cache_eligible=True,
        user_message_limit=12000,
    )
    try:
        parsed = JobMatchExplainOutput.model_validate(_extract_json_object(routed.get("content") or ""))
    except ValidationError as exc:
        raise WorkflowError(
            f"Job match explain schema validation failed: {exc.errors()[0]['msg']}",
            status_code=422,
        ) from exc
    return {
        "explanation": parsed.explanation.strip(),
        "prompt_id": record.prompt_id,
        "prompt_version": record.version,
        "provider": routed.get("provider"),
        "model_id": routed.get("model_id"),
        "prompt_tokens": routed.get("prompt_tokens"),
        "completion_tokens": routed.get("completion_tokens"),
        "total_tokens": routed.get("total_tokens"),
        "cache_status": routed.get("cache_status"),
        "escalation": routed.get("escalation"),
        "provider_request_id": routed.get("provider_request_id"),
    }
