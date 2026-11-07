"""Build a case summary only from collected source facts. No invented events."""

from __future__ import annotations

import hashlib
import json
from typing import Any

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


def source_fingerprint(packet: dict[str, Any]) -> str:
    material = json.dumps(packet.get("sources") or [], sort_keys=True, default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _lines(items: list[dict[str, Any]], formatter) -> str:
    if not items:
        return UNAVAILABLE
    return "\n".join(f"- {formatter(item)}" for item in items)


def compose_case_summary(packet: dict[str, Any]) -> dict[str, Any]:
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

    events = []
    events.extend(meetings)
    events.extend(incidents)
    events.extend(complaints)
    events_text = _lines(
        events,
        lambda item: f"{item.get('kind')}: {item.get('title')} ({item.get('when') or 'date not recorded'}, status {item.get('status')})",
    )
    recent = _lines(
        notes,
        lambda item: (
            f"{item.get('log_date')}: {item.get('summary')}"
            + (f" — {item['notes']}" if item.get("notes") else "")
            + f" [{item.get('status')}]"
        ),
    )
    needs = _lines(
        plans + goals,
        lambda item: (
            f"{item.get('kind')}: {item.get('title')} ({item.get('status')})"
            + (f" — {item['objectives']}" if item.get("objectives") else "")
        ),
    )
    open_follow = [item for item in follow_ups if item.get("status") not in {"completed", "cancelled"}]
    outstanding = _lines(
        open_follow,
        lambda item: f"Follow-up due {item.get('due_at') or 'unspecified'}: {item.get('action')} ({item.get('status')})",
    )
    upcoming_items = [
        item
        for item in appointments + meetings
        if item.get("status") in {"scheduled", "confirmed"}
    ]
    upcoming = _lines(
        upcoming_items,
        lambda item: f"{item.get('kind')} {item.get('when') or 'time not recorded'}: {item.get('title')} ({item.get('status')})",
    )

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

    if documents:
        doc_line = _lines(documents, lambda item: f"{item.get('title')} ({item.get('status')})")
        background = (background + " Document metadata: " + doc_line) if background != UNAVAILABLE else f"Document metadata:\n{doc_line}"

    sections = {
        "overview": overview,
        "background": background,
        "events": events_text,
        "recent_support": recent,
        "needs_and_goals": needs,
        "outstanding_actions": outstanding,
        "upcoming": upcoming,
    }
    for key in REQUIRED_SECTIONS:
        if not str(sections.get(key) or "").strip():
            sections[key] = UNAVAILABLE

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
