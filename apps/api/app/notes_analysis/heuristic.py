"""Local grounded heuristic for notes analysis when AI service is unavailable (dev/test).

Mirrors the AI-service structured_heuristic rules. Production should call the
shared AI service; this path is for offline tests and misconfigured local boots.
"""

from __future__ import annotations

import re
from typing import Any


def build_heuristic_analysis(note: dict[str, Any]) -> dict[str, Any]:
    summary_line = (note.get("summary") or "").strip()
    notes_body = (note.get("notes") or "").strip()
    category = (note.get("activity_category") or "").strip()
    interaction = (note.get("interaction_type") or "").strip()
    follow_up = bool(note.get("follow_up_required"))
    next_action = (note.get("next_action") or "").strip()
    log_date = str(note.get("log_date") or "")

    parts = [
        "AI-generated summary (structured heuristic — not a staff statement).",
        f"Log date: {log_date or 'not recorded'}.",
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

    missing: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    if follow_up and not next_action:
        missing.append(
            {
                "title": "Follow-up next action not recorded",
                "body": "The note marks follow-up as required but the next action field is empty.",
                "rationale": "Explicit follow_up_required=true without next_action text.",
                "source_excerpt": "follow_up_required=true",
                "is_interpretation": False,
            }
        )
        actions.append(
            {
                "title": "Record a concrete next action",
                "body": "Ask the authoring support worker to record who will act, what is needed, and by when.",
                "rationale": "Follow-up is flagged without an actionable next step on the source note.",
                "source_excerpt": "follow_up_required=true; next_action empty",
                "is_interpretation": True,
            }
        )
    if not notes_body:
        missing.append(
            {
                "title": "Detailed notes body empty",
                "body": "The structured notes field has no content.",
                "rationale": "notes field is empty on the source record.",
                "source_excerpt": None,
                "is_interpretation": False,
            }
        )
    blob = f"{notes_body} {summary_line}".lower()
    if "meeting" in blob and not re.search(
        r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b|\b\d{4}-\d{2}-\d{2}\b",
        f"{notes_body} {summary_line}",
    ):
        missing.append(
            {
                "title": "Meeting referenced without a clear date in free text",
                "body": "The note mentions a meeting but no clear date pattern was found.",
                "rationale": "Keyword 'meeting' present without an obvious date token.",
                "source_excerpt": "meeting",
                "is_interpretation": True,
            }
        )
    if follow_up:
        actions.append(
            {
                "title": "Create or review a follow-up task",
                "body": "Consider creating a follow-up task through the authorised operations module after human review.",
                "rationale": "Source note explicitly requires follow-up.",
                "source_excerpt": "follow_up_required=true",
                "is_interpretation": True,
            }
        )

    return {
        "analysis": {
            "summary": " ".join(parts),
            "key_observations": observations,
            "missing_details": missing,
            "suggested_actions": actions,
            "uncertainty_notes": (
                "This analysis used structured field heuristics only. "
                "It is AI-generated assistance for human review, not a verified staff statement."
            ),
            "generation_method": "structured_heuristic",
        },
        "prompt_id": "hmore.notes_analysis.v1",
        "prompt_version": "1.0.0",
        "provider": "heuristic",
        "model_id": "structured_heuristic_v1",
        "generation_method": "structured_heuristic",
        "ai_generated_label": True,
    }
