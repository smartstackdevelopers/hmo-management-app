"""F3.7 support-plan draft. Records are untrusted data and cannot approve a plan."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.core.errors import WorkflowError
from app.prompts.store import get_prompt_store
from app.routing.executor import run_routed_completion

PROMPT_ID = "hmore.support_plan_draft.v1"
PROMPT_VERSION = "1.0.0"
DECISION_LANGUAGE = re.compile(
    r"diagnos|eligib|safeguarding determination|clinical decision|risk level|housing decision",
    re.IGNORECASE,
)


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., min_length=1, max_length=64)
    id: str = Field(..., min_length=1, max_length=64)


class MilestoneSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class GoalSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=4000)
    intended_outcome: str | None = None
    actions: list[str] = Field(default_factory=list)
    milestones: list[MilestoneSuggestion] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(..., min_length=1)


class DraftContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    situation: str = Field(..., min_length=1, max_length=4000)
    recorded_needs: list[str] = Field(default_factory=list)
    recorded_strengths: list[str] = Field(default_factory=list)
    recorded_goals: list[str] = Field(default_factory=list)
    suggested_goals: list[GoalSuggestion] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    responsibility_note: str = Field(..., min_length=1, max_length=500)
    review_note: str | None = None


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise WorkflowError("Support plan draft output is not valid JSON", status_code=422)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise WorkflowError("Support plan draft output JSON could not be parsed", status_code=422) from exc
    if not isinstance(data, dict):
        raise WorkflowError("Support plan draft output must be a JSON object", status_code=422)
    return data


def validate_draft(payload: dict[str, Any], allowed_ids: set[str]) -> DraftContent:
    content = payload.get("content") if isinstance(payload.get("content"), dict) else payload
    try:
        parsed = DraftContent.model_validate(content)
    except ValidationError as exc:
        raise WorkflowError("Support plan draft schema validation failed", status_code=422) from exc
    if DECISION_LANGUAGE.search(parsed.model_dump_json()):
        raise WorkflowError("Support plan draft states a decision", status_code=422)
    for goal in parsed.suggested_goals:
        if any(ref.id not in allowed_ids for ref in goal.source_refs):
            raise WorkflowError("Suggestion cites an unknown source", status_code=422)
    return parsed


def heuristic_draft(packet: dict[str, Any]) -> DraftContent:
    profile = packet.get("profile") or {}
    name = profile.get("preferred_name") or "Unnamed tenant record"
    needs = str(profile.get("needs_goals") or "").strip()
    tenant_id = str(profile.get("id") or "")
    goals = [str(item.get("title")) for item in (packet.get("goals") or []) if item.get("title")]
    suggested = []
    gaps = []
    if needs and tenant_id:
        suggested.append(
            GoalSuggestion(
                title=needs[:80],
                description=f"Suggested from recorded needs text. Recorded text: {needs[:500]}",
                actions=["Staff confirm this wording before it is added to the support plan."],
                milestones=[MilestoneSuggestion(title="Staff confirm the recorded need", description="No date is proposed.")],
                source_refs=[SourceRef(type="tenant", id=tenant_id)],
            )
        )
    else:
        gaps.append("No needs text is stored. A goal was not invented.")
    # Note text is untrusted and is not copied into the suggestion.
    _ = packet.get("daily_notes")
    return DraftContent(
        situation=f"Draft assistance for {name}. This is an AI draft, not an approved support plan.",
        recorded_needs=[needs[:500]] if needs else [],
        recorded_goals=goals[:20],
        suggested_goals=suggested,
        gaps=gaps,
        responsibility_note="This draft does not assign a staff member.",
        review_note="Review dates are not proposed.",
    )


def run_support_plan_draft(*, settings: Settings, organisation_id, packet: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, dict) or not packet.get("profile"):
        raise WorkflowError("support_plan_draft requires input_payload.packet.profile", status_code=422)
    allowed = {str(item.get("id")) for item in (packet.get("sources") or []) if item.get("id")}
    store = get_prompt_store()
    record, rendered = store.render(
        PROMPT_ID,
        variables={
            "organisation_id": str(organisation_id),
            "packet_json": json.dumps(packet, default=str)[:6000],
        },
    )
    parsed = heuristic_draft(packet)
    provider = "heuristic"
    model_id = "structured_heuristic_v1"
    generation_method = "structured_heuristic"
    prompt_tokens = completion_tokens = total_tokens = None
    cache_status = escalation = provider_request_id = None
    if settings.llm_provider == "openai":
        routed = run_routed_completion(
            settings=settings,
            organisation_id=organisation_id,
            workflow_id="support_plan_draft",
            prompt_id=record.prompt_id,
            prompt_version=record.version,
            rendered_prompt=rendered,
            user_message="Produce the support plan draft JSON from the authorised packet only.",
            quality_requirement="standard",
            cache_eligible=True,
        )
        parsed = validate_draft(_extract_json(routed.get("content") or ""), allowed)
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
        "draft": {"content": parsed.model_dump(), "generation_method": generation_method},
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
