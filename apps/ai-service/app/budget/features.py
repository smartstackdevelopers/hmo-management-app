"""Feature attribution helpers shared with core API conventions (F3.3)."""

from __future__ import annotations

FEATURE_FOUNDATION = "ai.infra.foundation"
FEATURE_ROUTING = "ai.infra.routing"
FEATURE_NOTES_ANALYSIS = "ai.agent.notes_analysis"
FEATURE_CASE_SUMMARY = "ai.workflow.case_summaries"
FEATURE_DOCUMENT_CHECK = "ai.workflow.document_checker"
FEATURE_SUPPORT_PLANNING = "ai.agent.support_planning"
FEATURE_HOUSING_APPLICATION = "ai.agent.housing_application"
FEATURE_COMPLIANCE = "ai.agent.compliance"
FEATURE_UNKNOWN = "ai.infra.unattributed"

WORKFLOW_FEATURE_MAP: dict[str, str] = {
    "foundation_ping": FEATURE_FOUNDATION,
    "foundation_echo": FEATURE_FOUNDATION,
    "foundation_routed_echo": FEATURE_ROUTING,
    "notes_analysis": FEATURE_NOTES_ANALYSIS,
    "case_summary": FEATURE_CASE_SUMMARY,
    "document_check": FEATURE_DOCUMENT_CHECK,
    "support_plan_draft": FEATURE_SUPPORT_PLANNING,
    "housing_application_analysis": FEATURE_HOUSING_APPLICATION,
    "compliance_explanation": FEATURE_COMPLIANCE,
}


def feature_for_workflow(workflow_id: str) -> str:
    return WORKFLOW_FEATURE_MAP.get(workflow_id, FEATURE_UNKNOWN)
