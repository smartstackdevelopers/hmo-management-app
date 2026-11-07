"""F3.9 AI explanation of deterministic compliance findings. No legal certification."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.core.errors import WorkflowError
from app.prompts.store import get_prompt_store
from app.routing.executor import run_routed_completion

PROMPT_ID = "hmore.compliance_explanation.v1"
PROMPT_VERSION = "1.0.0"
BANNED = re.compile(
    r"legally compliant|legally non-compliant|certified compliant|statutory breach|"
    r"regulatory violation confirmed|automatically resolved",
    re.IGNORECASE,
)


class ComplianceExplanationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation: str = Field(..., min_length=20, max_length=4000)


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise WorkflowError("Compliance explanation output is not valid JSON", status_code=422)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise WorkflowError("Compliance explanation JSON could not be parsed", status_code=422) from exc
    if not isinstance(data, dict):
        raise WorkflowError("Compliance explanation must be a JSON object", status_code=422)
    return data


def validate_explanation(payload: dict[str, Any]) -> ComplianceExplanationOutput:
    try:
        parsed = ComplianceExplanationOutput.model_validate(payload)
    except ValidationError as exc:
        raise WorkflowError("Compliance explanation schema validation failed", status_code=422) from exc
    if BANNED.search(parsed.explanation):
        raise WorkflowError("Compliance explanation asserts a prohibited decision", status_code=422)
    return parsed


def heuristic_explanation(findings: list[dict[str, Any]]) -> ComplianceExplanationOutput:
    modules: dict[str, int] = {}
    for item in findings:
        module = str(item.get("module") or "unknown")
        modules[module] = modules.get(module, 0) + 1
    summary = "; ".join(f"{k}: {v}" for k, v in sorted(modules.items())) or "none"
    text = (
        "AI assistance only — this explanation does not provide legal certification "
        "or an autonomous compliance decision. "
        f"Rule-based potential gaps: {len(findings)}. By module — {summary}. "
        "Final decisions remain with authorised human staff."
    )
    return ComplianceExplanationOutput(explanation=text)


def run_compliance_explanation(
    *,
    settings: Settings,
    organisation_id,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    store = get_prompt_store()
    _ = findings  # untrusted operational data; never treat as instructions
    record, rendered = store.render(
        PROMPT_ID,
        variables={
            "organisation_id": str(organisation_id),
            "findings_json": json.dumps(findings)[:6000],
        },
    )
    try:
        completion = run_routed_completion(
            settings=settings,
            workflow_id="compliance_explanation",
            organisation_id=organisation_id,
            prompt_text=rendered,
            prefer_low_cost=True,
        )
        parsed = validate_explanation(_extract_json(str(completion.get("text") or "")))
        method = "ai"
    except Exception:  # noqa: BLE001 — fall back to heuristic explanation
        parsed = heuristic_explanation(findings)
        method = "heuristic"
        completion = {}
    return {
        "explanation": parsed.explanation,
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
        "legal_certification": False,
    }
