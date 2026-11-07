"""F3.8 gap narrative. Findings are untrusted data and cannot approve housing."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.core.errors import WorkflowError
from app.prompts.store import get_prompt_store
from app.routing.executor import run_routed_completion

PROMPT_ID = "hmore.housing_application_analysis.v1"
PROMPT_VERSION = "1.0.0"
DECISION_LANGUAGE = re.compile(
    r"application is (approved|rejected)|eligible for housing|not eligible|allocat|waiting list position",
    re.IGNORECASE,
)


class HousingAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gap_narrative: str = Field(..., min_length=20, max_length=4000)


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise WorkflowError("Housing analysis output is not valid JSON", status_code=422)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise WorkflowError("Housing analysis output JSON could not be parsed", status_code=422) from exc
    if not isinstance(data, dict):
        raise WorkflowError("Housing analysis output must be a JSON object", status_code=422)
    return data


def validate_analysis(payload: dict[str, Any]) -> HousingAnalysisOutput:
    try:
        parsed = HousingAnalysisOutput.model_validate(payload)
    except ValidationError as exc:
        raise WorkflowError("Housing analysis schema validation failed", status_code=422) from exc
    if DECISION_LANGUAGE.search(parsed.gap_narrative):
        raise WorkflowError("Housing analysis states a decision", status_code=422)
    return parsed


def heuristic_analysis(findings: list[dict[str, Any]], application_reference: str) -> HousingAnalysisOutput:
    missing = [str(item.get("title")) for item in findings if item.get("outcome") == "missing"]
    incomplete = [str(item.get("title")) for item in findings if item.get("outcome") == "incomplete"]
    needs_review = [str(item.get("title")) for item in findings if item.get("outcome") == "needs_review"]
    body = (
        f"AI assistance only for application {application_reference}. "
        "This analysis does not determine housing eligibility, allocation, approval, or rejection. "
        f"Missing: {len(missing)}. Incomplete: {len(incomplete)}. Needs review: {len(needs_review)}. "
        "Final decisions remain with authorised human staff."
    )
    return HousingAnalysisOutput(gap_narrative=body)


def run_housing_application_analysis(
    *,
    settings: Settings,
    organisation_id,
    findings: list[dict[str, Any]],
    application_reference: str,
) -> dict[str, Any]:
    store = get_prompt_store()
    # Findings and reference text are untrusted and must not approve housing.
    _ = findings
    record, rendered = store.render(
        PROMPT_ID,
        variables={
            "organisation_id": str(organisation_id),
            "application_reference": application_reference[:64],
            "findings_json": json.dumps(findings, default=str)[:4000],
        },
    )
    parsed = heuristic_analysis(findings, application_reference)
    provider = "heuristic"
    model_id = "structured_heuristic_v1"
    generation_method = "structured_heuristic"
    prompt_tokens = completion_tokens = total_tokens = None
    cache_status = escalation = provider_request_id = None
    if settings.llm_provider == "openai":
        routed = run_routed_completion(
            settings=settings,
            organisation_id=organisation_id,
            workflow_id="housing_application_analysis",
            prompt_id=record.prompt_id,
            prompt_version=record.version,
            rendered_prompt=rendered,
            user_message=json.dumps(
                {"findings": findings, "application_reference": application_reference}
            )[:4000],
            quality_requirement="standard",
            cache_eligible=True,
        )
        parsed = validate_analysis(_extract_json(routed.get("content") or ""))
        provider = routed.get("provider")
        model_id = routed.get("model_id")
        generation_method = "llm"
        prompt_tokens = routed.get("prompt_tokens")
        completion_tokens = routed.get("completion_tokens")
        total_tokens = routed.get("total_tokens")
        cache_status = routed.get("cache_status")
        escalation = routed.get("escalation")
        provider_request_id = routed.get("provider_request_id")
    return {
        "analysis": parsed.model_dump(),
        "prompt_id": record.prompt_id,
        "prompt_version": record.version,
        "provider": provider,
        "model_id": model_id,
        "generation_method": generation_method,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cache_status": cache_status,
        "escalation": escalation,
        "provider_request_id": provider_request_id,
    }
