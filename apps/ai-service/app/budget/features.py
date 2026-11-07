"""Feature attribution helpers shared with core API conventions (F3.3)."""

from __future__ import annotations

FEATURE_FOUNDATION = "ai.infra.foundation"
FEATURE_ROUTING = "ai.infra.routing"
FEATURE_UNKNOWN = "ai.infra.unattributed"

WORKFLOW_FEATURE_MAP: dict[str, str] = {
    "foundation_ping": FEATURE_FOUNDATION,
    "foundation_echo": FEATURE_FOUNDATION,
    "foundation_routed_echo": FEATURE_ROUTING,
}


def feature_for_workflow(workflow_id: str) -> str:
    return WORKFLOW_FEATURE_MAP.get(workflow_id, FEATURE_UNKNOWN)
