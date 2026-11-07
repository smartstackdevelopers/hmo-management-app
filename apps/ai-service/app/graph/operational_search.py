"""F3.12 question interpretation. Returns a structured spec only — never SQL."""

from __future__ import annotations

import re
from typing import Any

_SQLISH = re.compile(r"\b(select|insert|update|delete|drop|alter|union)\b|;|--", re.I)

ENTITIES = {
    "maintenance_request",
    "complaint",
    "housing_application",
    "incident_follow_up",
    "support_plan",
    "operational_task",
    "managed_document",
    "staff_training",
}


def interpret_question(question: str) -> dict[str, Any]:
    text = " ".join((question or "").split()).lower()
    if not text:
        return {"outcome": "clarification", "message": "Enter a question about operational records."}
    if _SQLISH.search(text) and not any(
        word in text for word in ("maintenance", "complaint", "application", "incident", "task", "document", "training", "support plan")
    ):
        return {"outcome": "unsupported", "message": "That search is not supported."}
    found: set[str] = set()
    if "maintenance" in text or "repair" in text:
        found.add("maintenance_request")
    if "complaint" in text:
        found.add("complaint")
    if "application" in text or "waiting for approval" in text:
        found.add("housing_application")
    if "incident" in text or "follow-up" in text or "follow up" in text:
        found.add("incident_follow_up")
    if "support plan" in text:
        found.add("support_plan")
    if "task" in text:
        found.add("operational_task")
    if "document" in text:
        found.add("managed_document")
    if "training" in text:
        found.add("staff_training")
    if len(found) > 1:
        return {
            "outcome": "clarification",
            "message": "Name one record type so the search can stay within an allowlisted query.",
        }
    if not found:
        return {"outcome": "unsupported", "message": "That search is not supported."}
    entity = next(iter(found))
    preset = "open"
    if entity == "housing_application" and any(word in text for word in ("approval", "waiting", "pending", "awaiting")):
        preset = "awaiting_approval"
    elif entity == "incident_follow_up":
        preset = "outstanding_follow_up"
    elif entity in {"managed_document", "staff_training"} and "expir" in text:
        preset = "expiring_soon"
    elif "overdue" in text:
        preset = "overdue_open"
    elif "assigned" in text or text.startswith("my "):
        preset = "assigned_to_me"
    if entity not in ENTITIES:
        return {"outcome": "unsupported", "message": "That search is not supported."}
    return {
        "outcome": "ready",
        "entity": entity,
        "preset": preset,
        "limit": 25,
        "offset": 0,
        "sort": "oldest",
        "explanation": f"Search {entity.replace('_', ' ')} using the {preset.replace('_', ' ')} filter.",
    }


def run_operational_search(*, question: str) -> dict[str, Any]:
    spec = interpret_question(question)
    return {
        "specification": spec,
        "prompt_id": "operational_search",
        "prompt_version": "1",
        "provider": "deterministic",
        "model_id": "allowlist-parser",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cache_status": "miss",
        "executed_sql": False,
    }
