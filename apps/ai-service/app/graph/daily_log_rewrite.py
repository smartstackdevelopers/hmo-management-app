"""F4.4 optional professional rewrite of a draft daily note.

The model may improve grammar and clarity. It must not invent facts.
This module does not persist a daily log and does not attach fabricated
sources or a confidence score.
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

DAILY_LOG_REWRITE_PROMPT_ID = "hmore.daily_log_rewrite.v1"
DAILY_LOG_REWRITE_PROMPT_VERSION = "1.0.0"
MAX_TEXT = 20000


class DailyLogRewriteOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rewritten_text: str = Field(..., min_length=1, max_length=MAX_TEXT)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise WorkflowError("Daily log rewrite output is not valid JSON", status_code=422)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise WorkflowError("Daily log rewrite output JSON could not be parsed", status_code=422) from exc
    if not isinstance(data, dict):
        raise WorkflowError("Daily log rewrite output must be a JSON object", status_code=422)
    return data


def validate_daily_log_rewrite_output(payload: dict[str, Any]) -> DailyLogRewriteOutput:
    try:
        parsed = DailyLogRewriteOutput.model_validate(payload)
    except ValidationError as exc:
        raise WorkflowError(
            f"Daily log rewrite schema validation failed: {exc.errors()[0]['msg']}",
            status_code=422,
        ) from exc
    parsed.rewritten_text = parsed.rewritten_text.strip()
    if not parsed.rewritten_text:
        raise WorkflowError("Daily log rewrite text is empty", status_code=422)
    return parsed


def run_daily_log_rewrite(
    *,
    settings: Settings,
    organisation_id,
    text: str,
    locale: str | None = None,
) -> dict[str, Any]:
    """Rewrite draft note text. Raises when no model is configured.

    A missing model is not turned into a fake rewrite of the original text.
    """
    note = (text or "").strip()
    if not note:
        raise WorkflowError("daily_log_rewrite requires text", status_code=422)
    if len(note) > MAX_TEXT:
        raise WorkflowError("daily_log_rewrite text exceeds 20000 characters", status_code=422)

    if settings.llm_provider not in {"openai", "mock"}:
        raise WorkflowError(
            "AI professional rewrite is unavailable because no language model is configured",
            status_code=503,
        )

    locale_value = (str(locale).strip() if locale else "") or "en-GB"
    store = get_prompt_store()
    record, rendered = store.render(
        DAILY_LOG_REWRITE_PROMPT_ID,
        variables={
            "organisation_id": str(organisation_id),
            "locale": locale_value[:35],
        },
    )
    routed = run_routed_completion(
        settings=settings,
        organisation_id=organisation_id,
        workflow_id="daily_log_rewrite",
        prompt_id=record.prompt_id,
        prompt_version=record.version,
        rendered_prompt=rendered,
        user_message=note,
        quality_requirement="standard",
        cache_eligible=False,
        user_message_limit=MAX_TEXT,
    )
    parsed = validate_daily_log_rewrite_output(_extract_json_object(routed.get("content") or ""))
    return {
        "rewritten_text": parsed.rewritten_text,
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
        "generation_method": "llm",
    }
