"""Controlled values for F3.14."""

from __future__ import annotations

FEEDBACK_CATEGORIES = frozenset(
    {
        "incorrect_information",
        "incomplete_answer",
        "misleading_answer",
        "unsupported_claim",
        "missing_source",
        "outdated_information",
        "other",
    }
)

FEEDBACK_REVIEW_STATUSES = frozenset(
    {
        "submitted",
        "under_review",
        "resolved",
        "rejected",
    }
)

# Features whose activity is visible only to the initiating user (plus feedback reviewers).
INITIATOR_VISIBILITY_FEATURES = frozenset(
    {
        "ai.agent.tenant_assistant",
    }
)

FEATURE_AGENT_NAMES = {
    "ai.agent.notes_analysis": "Notes Analysis Agent",
    "ai.agent.case_summary": "Case Summaries Workflow",
    "ai.agent.document_check": "Smart Document Checker",
    "ai.agent.support_plan_draft": "Support Planning Agent",
    "ai.agent.housing_application": "Housing Application Agent",
    "ai.agent.compliance": "Compliance Agent",
    "ai.agent.tenant_assistant": "Tenant Assistant",
    "ai.agent.operational_search": "Natural-Language Operational Search",
    "ai.agent.report_draft": "Weekly/Monthly Report Drafts",
    "ai.agent.duplicate_detection": "Duplicate Detection",
    "ai.workflow.daily_log_rewrite": "Daily Log Professional Rewrite",
}

MAX_FEEDBACK_EXPLANATION = 2000
MAX_FEEDBACK_PER_HOUR = 20
