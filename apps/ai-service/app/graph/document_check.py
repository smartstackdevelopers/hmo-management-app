"""F3.6 gap explanation. Document text is untrusted data and cannot approve anything."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.core.errors import WorkflowError
from app.prompts.store import get_prompt_store
from app.routing.executor import run_routed_completion

DOCUMENT_CHECK_PROMPT_ID = "hmore.document_check.v1"
DOCUMENT_CHECK_PROMPT_VERSION = "1.0.0"


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=1500)
    source_finding_code: str = Field(..., min_length=1, max_length=64)
    needs_human_verification: bool = True


class DocumentCheckAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: list[Observation] = Field(default_factory=list)


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise WorkflowError("Document check output is not valid JSON", status_code=422)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise WorkflowError("Document check output JSON could not be parsed", status_code=422) from exc
    if not isinstance(data, dict):
        raise WorkflowError("Document check output must be a JSON object", status_code=422)
    return data


def validate_analysis(payload: dict[str, Any], finding_codes: set[str]) -> DocumentCheckAnalysis:
    try:
        parsed = DocumentCheckAnalysis.model_validate(payload)
    except ValidationError as exc:
        raise WorkflowError("Document check schema validation failed", status_code=422) from exc
    for item in parsed.observations:
        if item.source_finding_code not in finding_codes:
            raise WorkflowError("Observation is not tied to a finding", status_code=422)
        lowered = item.body.lower()
        if re.search(r"document is (approved|valid)|eligib", lowered):
            raise WorkflowError("Observation states a decision", status_code=422)
    return parsed


def heuristic_analysis(findings: list[dict[str, Any]]) -> DocumentCheckAnalysis:
    observations = []
    for item in findings:
        if item.get("outcome") not in {"fail", "warning", "not_performed"}:
            continue
        observations.append(
            Observation(
                title=str(item.get("title") or item.get("code") or "Finding")[:200],
                body=(
                    "This restates a recorded check. It is not a new fact and it does not approve the document. "
                    + str(item.get("title") or "")
                )[:1500],
                source_finding_code=str(item.get("code")),
                needs_human_verification=True,
            )
        )
    return DocumentCheckAnalysis(observations=observations)


def run_document_check(*, settings: Settings, organisation_id, findings: list[dict[str, Any]], excerpt: str) -> dict[str, Any]:
    store = get_prompt_store()
    codes = {str(item.get("code")) for item in findings if item.get("code")}
    # Excerpt is untrusted. It is not passed to the heuristic and cannot change the result.
    _ = excerpt
    record, rendered = store.render(
        DOCUMENT_CHECK_PROMPT_ID,
        variables={
            "organisation_id": str(organisation_id),
            "findings_json": json.dumps(findings, default=str)[:4000],
            "excerpt": (excerpt or "")[:1500],
        },
    )
    provider = "heuristic"
    model_id = "structured_heuristic_v1"
    generation_method = "structured_heuristic"
    parsed = heuristic_analysis(findings)
    prompt_tokens = completion_tokens = total_tokens = None
    cache_status = escalation = provider_request_id = None
    if settings.llm_provider == "openai":
        routed = run_routed_completion(
            settings=settings,
            organisation_id=organisation_id,
            workflow_id="document_check",
            prompt_id=record.prompt_id,
            prompt_version=record.version,
            rendered_prompt=rendered,
            user_message=json.dumps({"findings": findings, "untrusted_excerpt": (excerpt or "")[:1500]})[:4000],
            quality_requirement="standard",
            cache_eligible=True,
        )
        parsed = validate_analysis(_extract_json(routed.get("content") or ""), codes)
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
