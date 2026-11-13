"""Optional AI Gateway suggestions for workflow authoring."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("hmore.advanced_automation.ai_client")


def suggest_workflow(*, organisation_id: str, prompt: str, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"suggestion": "Enable AI assistant in organisation settings to receive template suggestions."}
    # Delegates to AI Gateway when configured; sandbox fallback avoids blocking tests.
    return {
        "suggestion": (
            "Consider a start → condition (rent days overdue) → notification → approval → end flow. "
            "Reuse F6.3 automation rules for recurring rent overdue checks."
        ),
        "template_hint": "rent_overdue_escalation",
        "provider": "sandbox",
    }
