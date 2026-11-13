"""Approved-content voice assistant responses (no fabricated policies)."""

from __future__ import annotations

import re

from app.tenant_assistant.service import ESCALATION_MESSAGES, NOTICE

DISCLOSURE = (
    "You are speaking with the HMore automated voice assistant. "
    "This is not a human adviser. Calls are not recorded by default."
)

EMERGENCY_LINE = (
    "If you are in immediate danger, hang up and contact the emergency services on 999. "
    "This assistant cannot contact emergency services for you."
)


def normalize_transcript(text: str) -> str:
    return " ".join((text or "").strip().split())[:2000]


def generate_response(user_text: str, *, language: str) -> tuple[str, bool, str | None]:
    """Return assistant text, handover_suggested, handover_reason."""
    t = user_text.lower()
    if re.search(r"\b(999|emergency|fire|gas leak)\b", t):
        return EMERGENCY_LINE, True, "emergency_or_safety"
    if "human" in t or "speak to someone" in t or "adviser" in t:
        return ESCALATION_MESSAGES["human_support"], True, "human_support"
    if "complaint" in t or "safeguarding" in t:
        return ESCALATION_MESSAGES.get("safeguarding", ESCALATION_MESSAGES["human_support"]), True, "safeguarding"
    if "housing application" in t or "rehouse" in t or "allocate" in t:
        return ESCALATION_MESSAGES["housing_decision"], True, "housing_decision"
    if "repair" in t or "maintenance" in t or "broken" in t:
        return (
            "You can report a repair in the HMore app under Maintenance. "
            "I cannot log a repair during this call. Would you like a human team member to help?",
            "broken" in t or "urgent" in t,
            "maintenance_request" if "urgent" in t else None,
        )
    if "appointment" in t or "meeting" in t:
        return (
            "Appointments can be requested through your HMore profile or your support worker. "
            "I cannot book an appointment for you.",
            False,
            None,
        )
    if "food bank" in t or "community" in t:
        return (
            "You can find local food banks and services in the Community section of the HMore app. "
            "I only share organisation-approved listings.",
            False,
            None,
        )
    return (
        f"{NOTICE} Please ask about repairs, appointments, community services, or say 'human' for staff.",
        False,
        None,
    )
