"""Canonical AI feature identifiers for cost attribution (F3.3).

Future agents (F3.4+) must report one of these feature IDs (or a documented
shared-infrastructure ID) when calling the shared AI service. Do not invent
usage for agents that are not yet implemented.
"""

from __future__ import annotations

# Planned agents — reserved identifiers; no fabricated usage until implemented.
FEATURE_NOTES_ANALYSIS = "ai.agent.notes_analysis"
FEATURE_SUPPORT_PLANNING = "ai.agent.support_planning"
FEATURE_HOUSING_APPLICATION = "ai.agent.housing_application"
FEATURE_COMPLIANCE = "ai.agent.compliance"
FEATURE_JOB_MATCHING = "ai.agent.job_matching"
FEATURE_TENANT_ASSISTANT = "ai.agent.tenant_assistant"

# Shared infrastructure (F3.1 / F3.2 foundation workflows)
FEATURE_FOUNDATION = "ai.infra.foundation"
FEATURE_ROUTING = "ai.infra.routing"
FEATURE_BATCH = "ai.infra.batch"
FEATURE_CACHE = "ai.infra.cache"
FEATURE_CASE_SUMMARY = "ai.workflow.case_summaries"
FEATURE_DOCUMENT_CHECK = "ai.workflow.document_checker"
FEATURE_UNKNOWN = "ai.infra.unattributed"

PLANNED_AGENT_FEATURES: frozenset[str] = frozenset(
    {
        FEATURE_NOTES_ANALYSIS,
        FEATURE_SUPPORT_PLANNING,
        FEATURE_HOUSING_APPLICATION,
        FEATURE_COMPLIANCE,
        FEATURE_JOB_MATCHING,
        FEATURE_TENANT_ASSISTANT,
    }
)

INFRA_FEATURES: frozenset[str] = frozenset(
    {
        FEATURE_FOUNDATION,
        FEATURE_ROUTING,
        FEATURE_BATCH,
        FEATURE_CACHE,
        FEATURE_UNKNOWN,
    }
)

WORKFLOW_FEATURES: frozenset[str] = frozenset({FEATURE_CASE_SUMMARY, FEATURE_DOCUMENT_CHECK})

ALL_FEATURE_IDS: frozenset[str] = PLANNED_AGENT_FEATURES | INFRA_FEATURES | WORKFLOW_FEATURES

WORKFLOW_FEATURE_MAP: dict[str, str] = {
    "foundation_ping": FEATURE_FOUNDATION,
    "foundation_echo": FEATURE_FOUNDATION,
    "foundation_routed_echo": FEATURE_ROUTING,
    "notes_analysis": FEATURE_NOTES_ANALYSIS,
    "case_summary": FEATURE_CASE_SUMMARY,
    "document_check": FEATURE_DOCUMENT_CHECK,
}


def feature_for_workflow(workflow_id: str) -> str:
    return WORKFLOW_FEATURE_MAP.get(workflow_id, FEATURE_UNKNOWN)
