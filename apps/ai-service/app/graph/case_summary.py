"""F3.5 case summary workflow.

Grounded output is built only from the authorised packet. An OpenAI response
that fails schema or source-id checks is an error — it is not replaced with a
success result. Heuristic output is used only when no real provider is configured.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.core.errors import ProviderError, WorkflowError
from app.prompts.store import get_prompt_store
from app.routing.executor import run_routed_completion

CASE_SUMMARY_PROMPT_ID = "hmore.case_summary.v1"
CASE_SUMMARY_PROMPT_VERSION = "1.0.0"
UNAVAILABLE = "Unavailable — no authorised records of this type were found for this case."
REQUIRED_SECTIONS = (
    "overview",
    "background",
    "events",
    "recent_support",
    "needs_and_goals",
    "outstanding_actions",
    "upcoming",
)


class ConcernItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1, max_length=2000)
    source_type: str = Field(..., min_length=1, max_length=64)
    source_id: str = Field(..., min_length=1, max_length=64)
    explicitly_recorded: bool


class CaseSummaryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: dict[str, str]
    missing_information: list[str] = Field(default_factory=list)
    recorded_concerns: list[ConcernItem] = Field(default_factory=list)
    covered_from: str | None = None
    covered_to: str | None = None
    uncertainty_notes: str | None = None
    generation_method: str = "llm"
    ai_generated: bool = True


def _lines(items: list[dict[str, Any]], formatter) -> str:
    if not items:
        return UNAVAILABLE
    return "\n".join(f"- {formatter(item)}" for item in items)


def grounded_case_summary(packet: dict[str, Any]) -> dict[str, Any]:
    """Same grounded composer as the core API heuristic. No invented events."""
    profile = packet.get("profile") or {}
    notes = packet.get("daily_notes") or []
    meetings = packet.get("meetings") or []
    appointments = packet.get("appointments") or []
    plans = packet.get("support_plans") or []
    goals = packet.get("goals") or []
    follow_ups = packet.get("follow_ups") or []
    incidents = packet.get("incidents") or []
    complaints = packet.get("complaints") or []
    maintenance = packet.get("maintenance") or []
    documents = packet.get("documents") or []
    name = profile.get("preferred_name") or "Unnamed tenant record"
    status = profile.get("status") or "unknown"
    overview = (
        f"AI-generated case summary for {name}. Record status: {status}. "
        "This is not a verified staff statement and does not change case records."
    )
    background_bits = []
    if profile.get("tenancy_reference"):
        background_bits.append(f"Tenancy reference on file: {profile['tenancy_reference']}.")
    if profile.get("needs_goals"):
        background_bits.append(f"Profile needs/goals text: {profile['needs_goals']}.")
    background = " ".join(background_bits) if background_bits else UNAVAILABLE
    events = list(meetings) + list(incidents) + list(complaints)
    sections = {
        "overview": overview,
        "background": background,
        "events": _lines(
            events,
            lambda item: f"{item.get('kind')}: {item.get('title')} ({item.get('when') or 'date not recorded'}, status {item.get('status')})",
        ),
        "recent_support": _lines(
            notes,
            lambda item: f"{item.get('log_date')}: {item.get('summary')}"
            + (f" — {item['notes']}" if item.get("notes") else "")
            + f" [{item.get('status')}]",
        ),
        "needs_and_goals": _lines(
            list(plans) + list(goals),
            lambda item: f"{item.get('kind')}: {item.get('title')} ({item.get('status')})"
            + (f" — {item['objectives']}" if item.get("objectives") else ""),
        ),
        "outstanding_actions": _lines(
            [item for item in follow_ups if item.get("status") not in {"completed", "cancelled"}],
            lambda item: f"Follow-up due {item.get('due_at') or 'unspecified'}: {item.get('action')} ({item.get('status')})",
        ),
        "upcoming": _lines(
            [item for item in list(appointments) + list(meetings) if item.get("status") in {"scheduled", "confirmed"}],
            lambda item: f"{item.get('kind')} {item.get('when') or 'time not recorded'}: {item.get('title')} ({item.get('status')})",
        ),
    }
    if documents:
        doc_line = _lines(documents, lambda item: f"{item.get('title')} ({item.get('status')})")
        sections["background"] = (
            sections["background"] + " Document metadata: " + doc_line
            if sections["background"] != UNAVAILABLE
            else f"Document metadata:\n{doc_line}"
        )
    for key in REQUIRED_SECTIONS:
        if not str(sections.get(key) or "").strip():
            sections[key] = UNAVAILABLE
    missing: list[str] = []
    if not notes:
        missing.append("No active daily notes were found for this case.")
    if not plans and not goals and not profile.get("needs_goals"):
        missing.append("No support plan, goal, or profile needs text was found.")
    if not meetings and not appointments:
        missing.append("No meetings or appointments were found.")
    concerns = []
    for item in incidents:
        concerns.append(
            {
                "text": f"Incident recorded: {item.get('title')} (severity {item.get('severity')}, status {item.get('status')}).",
                "source_type": "incident",
                "source_id": item.get("id"),
                "explicitly_recorded": True,
            }
        )
    for item in complaints:
        concerns.append(
            {
                "text": f"Complaint recorded: {item.get('title')} (status {item.get('status')}).",
                "source_type": "complaint",
                "source_id": item.get("id"),
                "explicitly_recorded": True,
            }
        )
    for item in maintenance:
        if item.get("priority") in {"high", "urgent", "emergency"}:
            concerns.append(
                {
                    "text": f"Maintenance request recorded: {item.get('title')} (priority {item.get('priority')}, status {item.get('status')}).",
                    "source_type": "maintenance",
                    "source_id": item.get("id"),
                    "explicitly_recorded": True,
                }
            )
    dates = [item.get("when") for item in notes + meetings + appointments + incidents + complaints if item.get("when")]
    return {
        "sections": sections,
        "missing_information": missing,
        "recorded_concerns": concerns,
        "covered_from": min(dates) if dates else None,
        "covered_to": max(dates) if dates else None,
        "uncertainty_notes": (
            "Generated only from authorised records supplied in the source packet. "
            "Empty sections mean those records were not found. This is not a diagnosis, "
            "safeguarding conclusion, legal finding, or risk classification."
        ),
        "generation_method": "structured_heuristic",
        "ai_generated": True,
    }


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise WorkflowError("Case summary output is not valid JSON", status_code=422)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise WorkflowError("Case summary output JSON could not be parsed", status_code=422) from exc
    if not isinstance(data, dict):
        raise WorkflowError("Case summary output must be a JSON object", status_code=422)
    return data


def validate_case_summary_output(payload: dict[str, Any], packet: dict[str, Any]) -> CaseSummaryOutput:
    try:
        parsed = CaseSummaryOutput.model_validate(payload)
    except ValidationError as exc:
        raise WorkflowError("Case summary schema validation failed", status_code=422) from exc
    for key in REQUIRED_SECTIONS:
        if not str(parsed.sections.get(key) or "").strip():
            raise WorkflowError("Case summary is missing a required section", status_code=422)
    allowed = {str(item.get("id")) for item in (packet.get("sources") or []) if item.get("id")}
    for concern in parsed.recorded_concerns:
        if concern.explicitly_recorded is not True or concern.source_id not in allowed:
            raise WorkflowError("Case summary concern is not traceable to a source record", status_code=422)
    return parsed


def run_case_summary(*, settings: Settings, organisation_id, packet: dict[str, Any]) -> dict[str, Any]:
    store = get_prompt_store()
    record, rendered = store.render(
        CASE_SUMMARY_PROMPT_ID,
        variables={
            "organisation_id": str(organisation_id),
            "packet_json": json.dumps(packet, default=str)[:8000],
        },
    )
    grounded = grounded_case_summary(packet)
    provider = "heuristic"
    model_id = "structured_heuristic_v1"
    prompt_tokens = None
    completion_tokens = None
    total_tokens = None
    cache_status = None
    escalation = None
    provider_request_id = None
    summary = grounded
    generation_method = "structured_heuristic"

    if settings.llm_provider == "openai":
        routed = run_routed_completion(
            settings=settings,
            organisation_id=organisation_id,
            workflow_id="case_summary",
            prompt_id=record.prompt_id,
            prompt_version=record.version,
            rendered_prompt=rendered,
            user_message=json.dumps(packet, default=str)[:4000],
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
        try:
            parsed = validate_case_summary_output(_extract_json_object(routed.get("content") or ""), packet)
        except (WorkflowError, ProviderError, ValidationError, json.JSONDecodeError) as exc:
            if isinstance(exc, WorkflowError):
                raise
            raise WorkflowError("Case summary output failed validation", status_code=422) from exc
        parsed.generation_method = "llm"
        summary = parsed.model_dump()
        generation_method = "llm"

    return {
        "summary": summary,
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
