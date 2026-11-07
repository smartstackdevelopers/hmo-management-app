"""F3.4 Notes Analysis LangGraph-style workflow helpers.

Produces validated structured output only. Never invents clinical diagnoses,
housing decisions, or risk classifications. Heuristic path uses only explicit
note fields when an LLM is unavailable or returns invalid JSON.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import Settings
from app.core.errors import ProviderError, WorkflowError
from app.prompts.store import get_prompt_store
from app.routing.executor import run_routed_completion

NOTES_ANALYSIS_PROMPT_ID = "hmore.notes_analysis.v1"
NOTES_ANALYSIS_PROMPT_VERSION = "1.0.0"


class MissingDetailItem(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=2000)
    rationale: str = Field(..., min_length=1, max_length=2000)
    source_excerpt: str | None = Field(default=None, max_length=500)
    is_interpretation: bool = True


class SuggestedActionItem(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=2000)
    rationale: str = Field(..., min_length=1, max_length=2000)
    source_excerpt: str | None = Field(default=None, max_length=500)
    is_interpretation: bool = True


class NotesAnalysisOutput(BaseModel):
    summary: str = Field(..., min_length=1, max_length=4000)
    key_observations: list[str] = Field(default_factory=list, max_length=20)
    missing_details: list[MissingDetailItem] = Field(default_factory=list, max_length=20)
    suggested_actions: list[SuggestedActionItem] = Field(default_factory=list, max_length=20)
    uncertainty_notes: str | None = Field(default=None, max_length=2000)
    generation_method: str = Field(default="llm")

    @field_validator("key_observations")
    @classmethod
    def _trim_obs(cls, value: list[str]) -> list[str]:
        return [v.strip() for v in value if v and v.strip()][:20]


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise WorkflowError("Notes analysis output is not valid JSON", status_code=422)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise WorkflowError("Notes analysis output JSON could not be parsed", status_code=422) from exc
    if not isinstance(data, dict):
        raise WorkflowError("Notes analysis output must be a JSON object", status_code=422)
    return data


def validate_notes_analysis_output(payload: dict[str, Any]) -> NotesAnalysisOutput:
    try:
        return NotesAnalysisOutput.model_validate(payload)
    except ValidationError as exc:
        raise WorkflowError(f"Notes analysis schema validation failed: {exc.errors()[0]['msg']}", status_code=422) from exc


def heuristic_notes_analysis(note: dict[str, Any]) -> NotesAnalysisOutput:
    """Grounded analysis from explicit note fields only — no invented facts."""
    summary_line = (note.get("summary") or "").strip()
    notes_body = (note.get("notes") or "").strip()
    category = (note.get("activity_category") or "").strip()
    interaction = (note.get("interaction_type") or "").strip()
    follow_up = bool(note.get("follow_up_required"))
    next_action = (note.get("next_action") or "").strip()
    log_date = str(note.get("log_date") or "")

    parts = [
        f"AI-generated summary (structured heuristic — not a staff statement).",
        f"Log date: {log_date or 'not recorded'}." if log_date else "Log date: not recorded.",
        f"Activity category: {category}." if category else "Activity category not recorded.",
        f"Staff summary line: {summary_line}." if summary_line else "No staff summary line recorded.",
    ]
    if notes_body:
        excerpt = notes_body if len(notes_body) <= 400 else notes_body[:397] + "..."
        parts.append(f"Recorded notes excerpt: {excerpt}")
    else:
        parts.append("Detailed notes body is empty.")
    if interaction:
        parts.append(f"Interaction type: {interaction}.")
    if follow_up:
        parts.append("Follow-up is marked as required.")
        if next_action:
            parts.append(f"Recorded next action: {next_action}.")
        else:
            parts.append("No next action text is recorded despite follow-up being required.")

    observations: list[str] = []
    if summary_line:
        observations.append(f"Recorded summary: {summary_line}")
    if follow_up:
        observations.append("Follow-up required flag is set on the source note")
    if next_action:
        observations.append(f"Next action field contains: {next_action}")

    missing: list[MissingDetailItem] = []
    actions: list[SuggestedActionItem] = []

    if follow_up and not next_action:
        missing.append(
            MissingDetailItem(
                title="Follow-up next action not recorded",
                body="The note marks follow-up as required but the next action field is empty.",
                rationale="Explicit follow_up_required=true without next_action text.",
                source_excerpt="follow_up_required=true",
                is_interpretation=False,
            )
        )
        actions.append(
            SuggestedActionItem(
                title="Record a concrete next action",
                body="Ask the authoring support worker to record who will act, what is needed, and by when.",
                rationale="Follow-up is flagged without an actionable next step on the source note.",
                source_excerpt="follow_up_required=true; next_action empty",
                is_interpretation=True,
            )
        )

    if not notes_body:
        missing.append(
            MissingDetailItem(
                title="Detailed notes body empty",
                body="The structured notes field has no content beyond (or instead of) the summary line.",
                rationale="notes field is empty on the source record.",
                source_excerpt=None,
                is_interpretation=False,
            )
        )

    if "meeting" in (notes_body + " " + summary_line).lower() and not re.search(
        r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b|\b\d{4}-\d{2}-\d{2}\b",
        notes_body + " " + summary_line,
    ):
        missing.append(
            MissingDetailItem(
                title="Meeting referenced without a clear date in free text",
                body="The note mentions a meeting but no clear date pattern was found in the note text.",
                rationale="Keyword 'meeting' present without an obvious date token in the source text.",
                source_excerpt="meeting",
                is_interpretation=True,
            )
        )

    if follow_up:
        actions.append(
            SuggestedActionItem(
                title="Create or review a follow-up task",
                body="Consider creating a follow-up task or appointment through the authorised operations module after human review.",
                rationale="Source note explicitly requires follow-up.",
                source_excerpt="follow_up_required=true",
                is_interpretation=True,
            )
        )

    return NotesAnalysisOutput(
        summary=" ".join(parts),
        key_observations=observations,
        missing_details=missing,
        suggested_actions=actions,
        uncertainty_notes=(
            "This analysis used structured field heuristics only. "
            "It is AI-generated assistance for human review, not a verified staff statement."
        ),
        generation_method="structured_heuristic",
    )


def run_notes_analysis(
    *,
    settings: Settings,
    organisation_id,
    note_payload: dict[str, Any],
) -> dict[str, Any]:
    """Execute notes analysis: prefer LLM JSON; fall back to grounded heuristic."""
    store = get_prompt_store()
    record, rendered = store.render(
        NOTES_ANALYSIS_PROMPT_ID,
        variables={
            "organisation_id": str(organisation_id),
            "note_json": json.dumps(note_payload, default=str)[:6000],
        },
    )

    use_llm = settings.llm_provider in {"openai", "mock"}
    generation_method = "llm"
    provider = None
    model_id = None
    prompt_tokens = None
    completion_tokens = None
    total_tokens = None
    cache_status = None
    escalation = None
    provider_request_id = None
    parsed: NotesAnalysisOutput

    if use_llm:
        try:
            routed = run_routed_completion(
                settings=settings,
                organisation_id=organisation_id,
                workflow_id="notes_analysis",
                prompt_id=record.prompt_id,
                prompt_version=record.version,
                rendered_prompt=rendered,
                user_message=json.dumps(note_payload, default=str)[:4000],
                quality_requirement="standard",
                cache_eligible=True,
            )
            provider = routed.get("provider")
            model_id = routed.get("model_id")
            prompt_tokens = routed.get("prompt_tokens")
            completion_tokens = routed.get("completion_tokens")
            total_tokens = routed.get("total_tokens")
            cache_status = routed.get("cache_status")
            escalation = routed.get("escalation")
            provider_request_id = routed.get("provider_request_id")
            content = routed.get("content") or ""
            if settings.llm_provider == "mock" or not content.strip().startswith("{") and "{" not in content:
                parsed = heuristic_notes_analysis(note_payload)
                generation_method = "structured_heuristic"
            else:
                parsed = validate_notes_analysis_output(_extract_json_object(content))
                parsed.generation_method = "llm"
                generation_method = "llm"
        except (WorkflowError, ProviderError, ValidationError, json.JSONDecodeError):
            parsed = heuristic_notes_analysis(note_payload)
            generation_method = "structured_heuristic"
    else:
        parsed = heuristic_notes_analysis(note_payload)
        generation_method = "structured_heuristic"
        provider = "heuristic"
        model_id = "structured_heuristic_v1"

    return {
        "analysis": parsed.model_dump(),
        "prompt_id": record.prompt_id,
        "prompt_version": record.version,
        "provider": provider,
        "model_id": model_id,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cache_status": cache_status,
        "escalation": escalation,
        "provider_request_id": provider_request_id,
        "generation_method": generation_method,
        "ai_generated_label": True,
    }
