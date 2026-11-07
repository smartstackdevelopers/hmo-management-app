"""Deterministic interpretation of staff questions into an allowlisted spec.

This never emits SQL. The AI service may return the same shape; the API re-validates it.
"""

from __future__ import annotations

import re
from typing import Any

from app.operational_search.catalog import DEFAULT_LIMIT, ENTITIES, MAX_LIMIT, PRESETS

_SQLISH = re.compile(r"\b(select|insert|update|delete|drop|alter|union)\b|;|--", re.I)


class SearchSpecError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _cues(question: str) -> set[str]:
    text = question.lower()
    found: set[str] = set()
    if "maintenance" in text or "repair" in text:
        found.add("maintenance_request")
    if "complaint" in text:
        found.add("complaint")
    if "housing application" in text or "application" in text or "waiting for approval" in text:
        found.add("housing_application")
    if "incident" in text or "follow-up" in text or "follow up" in text:
        found.add("incident_follow_up")
    if "support plan" in text:
        found.add("support_plan")
    if re.search(r"\btasks?\b", text):
        found.add("operational_task")
    if "document" in text:
        found.add("managed_document")
    if "training" in text:
        found.add("staff_training")
    return found


def interpret_question(question: str) -> dict[str, Any]:
    cleaned = " ".join((question or "").split())
    if not cleaned:
        return {"outcome": "clarification", "message": "Enter a question about operational records."}
    if len(cleaned) > 500:
        raise SearchSpecError("Question is too long")
    entities = _cues(cleaned)
    # "follow up" alone should not also force housing. Application cue is broad.
    text = cleaned.lower()
    if "incident" in text and "housing_application" in entities and "application" not in text:
        entities.discard("housing_application")
    if "support plan" in entities or "support plan" in text:
        entities.discard("operational_task")
    if len(entities) > 1 and not (
        len(entities) == 2 and "incident_follow_up" in entities and ("follow" in text)
    ):
        # Two unrelated domains.
        if len(entities) > 1:
            return {
                "outcome": "clarification",
                "message": "That question matches more than one record type. Name one: maintenance, complaints, housing applications, incidents, support plans, tasks, documents, or training.",
                "candidate_entities": sorted(entities),
            }
    if not entities:
        return {
            "outcome": "unsupported",
            "message": "That search is not supported. Ask about maintenance, complaints, housing applications, incidents, support plans, tasks, documents, or training.",
        }
    entity = next(iter(entities))
    preset = "open"
    if entity == "housing_application" and any(
        phrase in text for phrase in ("approval", "awaiting", "waiting", "pending")
    ):
        preset = "awaiting_approval"
    elif entity == "incident_follow_up":
        preset = "outstanding_follow_up"
    elif entity in {"managed_document", "staff_training"} and "expir" in text:
        preset = "expiring_soon"
    elif "overdue" in text or "not been updated" in text:
        preset = "overdue_open"
    elif entity == "operational_task" and any(word in text for word in ("my ", "assigned", "particular")):
        preset = "assigned_to_me"
    elif "open" in text or "still" in text:
        preset = "open"
    if entity == "operational_task" and preset == "open" and "assigned" in text:
        preset = "assigned_to_me"
    return {
        "outcome": "ready",
        "entity": entity,
        "preset": preset,
        "limit": DEFAULT_LIMIT,
        "offset": 0,
        "sort": "oldest",
        "explanation": f"Search {entity.replace('_', ' ')} using the {preset.replace('_', ' ')} filter.",
    }


def validate_spec(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SearchSpecError("Search specification must be an object")
    forbidden = {"sql", "query", "statement", "table", "column", "organisation_id", "organization_id"}
    if forbidden & set(raw):
        raise SearchSpecError("Search specification contains forbidden fields")
    for value in raw.values():
        if isinstance(value, str) and _SQLISH.search(value):
            raise SearchSpecError("Search specification contains unsupported query text")
    outcome = raw.get("outcome")
    if outcome in {"clarification", "unsupported"}:
        message = str(raw.get("message") or "The question needs clarification.")
        if _SQLISH.search(message):
            raise SearchSpecError("Search specification contains unsupported query text")
        return {"outcome": outcome, "message": message[:500]}
    entity = raw.get("entity")
    preset = raw.get("preset")
    if entity not in ENTITIES:
        raise SearchSpecError("Unsupported entity")
    if preset not in PRESETS:
        raise SearchSpecError("Unsupported filter")
    try:
        limit = int(raw.get("limit", DEFAULT_LIMIT))
        offset = int(raw.get("offset", 0))
    except (TypeError, ValueError) as exc:
        raise SearchSpecError("Invalid pagination") from exc
    if limit < 1 or limit > MAX_LIMIT or offset < 0 or offset > 500:
        raise SearchSpecError("Result limit is outside the safe range")
    sort = raw.get("sort") or "oldest"
    if sort not in {"oldest", "newest"}:
        raise SearchSpecError("Unsupported sort")
    return {
        "outcome": "ready",
        "entity": entity,
        "preset": preset,
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "explanation": str(raw.get("explanation") or "")[:300],
    }
