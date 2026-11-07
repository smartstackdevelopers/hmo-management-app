"""Draft content is built only from authorised source ids. No invented dates or assignments."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

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
    description: str | None = Field(default=None, max_length=2000)


class GoalSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=4000)
    intended_outcome: str | None = Field(default=None, max_length=2000)
    actions: list[str] = Field(default_factory=list, max_length=8)
    milestones: list[MilestoneSuggestion] = Field(default_factory=list, max_length=6)
    source_refs: list[SourceRef] = Field(..., min_length=1, max_length=8)


class DraftContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    situation: str = Field(..., min_length=1, max_length=4000)
    recorded_needs: list[str] = Field(default_factory=list, max_length=12)
    recorded_strengths: list[str] = Field(default_factory=list, max_length=12)
    recorded_goals: list[str] = Field(default_factory=list, max_length=20)
    suggested_goals: list[GoalSuggestion] = Field(default_factory=list, max_length=8)
    gaps: list[str] = Field(default_factory=list, max_length=20)
    responsibility_note: str = Field(..., min_length=1, max_length=500)
    review_note: str | None = Field(default=None, max_length=500)


def source_ids(packet: dict[str, Any]) -> set[str]:
    return {str(item.get("id")) for item in (packet.get("sources") or []) if item.get("id")}


def validate_draft_content(payload: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    try:
        parsed = DraftContent.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Support plan draft schema validation failed") from exc
    allowed = source_ids(packet)
    blob = parsed.model_dump_json()
    if DECISION_LANGUAGE.search(blob):
        raise ValueError("Support plan draft states a decision the agent cannot make")
    for goal in parsed.suggested_goals:
        for ref in goal.source_refs:
            if ref.id not in allowed:
                raise ValueError("Suggestion cites a source that is not in the authorised packet")
        for action in goal.actions:
            if DECISION_LANGUAGE.search(action):
                raise ValueError("Suggested action states a decision the agent cannot make")
    return parsed.model_dump()


def compose_support_plan_draft(packet: dict[str, Any]) -> dict[str, Any]:
    """Restate recorded needs. Do not invent deadlines, percentages, or staff assignments."""
    profile = packet.get("profile") or {}
    name = profile.get("preferred_name") or "Unnamed tenant record"
    status = profile.get("status") or "unknown"
    needs = (profile.get("needs_goals") or "").strip()
    tenant_id = str(profile.get("id") or "")
    goals = packet.get("goals") or []
    notes = packet.get("daily_notes") or []
    plans = packet.get("support_plans") or []
    summaries = packet.get("approved_case_summaries") or []

    recorded_goals = [str(item.get("title")) for item in goals if item.get("title")]
    gaps: list[str] = []
    recorded_needs: list[str] = []
    recorded_strengths: list[str] = []
    suggested: list[dict[str, Any]] = []

    if needs and tenant_id:
        recorded_needs.append(needs[:500])
        suggested.append(
            {
                "title": needs[:80],
                "description": (
                    "Suggested from recorded needs text. This is not a new fact and does not assign staff. "
                    f"Recorded text: {needs[:500]}"
                ),
                "intended_outcome": None,
                "actions": ["Staff confirm this wording before it is added to the support plan."],
                "milestones": [
                    {
                        "title": "Staff confirm the recorded need",
                        "description": "No date was stored, so none is proposed.",
                    }
                ],
                "source_refs": [{"type": "tenant", "id": tenant_id}],
            }
        )
    else:
        gaps.append("No needs text is stored on the tenant record. A goal was not invented.")

    if not recorded_goals:
        gaps.append("No support-plan goals are recorded.")
    if not notes:
        gaps.append("No daily notes were available.")
    if not plans:
        gaps.append("No support plan is recorded. Suggestions cannot be applied until a plan exists.")
    if not recorded_strengths:
        gaps.append("No strengths were recorded, so none are listed.")
    if summaries:
        gaps.append("An approved case summary exists. It is a source reference, not a new fact.")

    situation = (
        f"Draft assistance for {name}. Record status: {status}. "
        "This is an AI draft, not an approved support plan."
    )
    content = {
        "situation": situation,
        "recorded_needs": recorded_needs,
        "recorded_strengths": recorded_strengths,
        "recorded_goals": recorded_goals[:20],
        "suggested_goals": suggested,
        "gaps": gaps,
        "responsibility_note": "This draft does not assign a staff member.",
        "review_note": "Review dates are not proposed unless staff enter them on the support plan.",
    }
    return {
        "content": validate_draft_content(content, packet),
        "generation_method": "structured_heuristic",
        "ai_generated": True,
    }
