"""Central registry of organisation-controllable AI features (F3.15).

F3.1–F3.3 shared infrastructure is platform-scoped and is NOT toggled per org here.
F3.15 itself is never registered — admins must not lock themselves out.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai_usage.features import (
    FEATURE_CASE_SUMMARY,
    FEATURE_COMPLIANCE,
    FEATURE_DAILY_LOG_REWRITE,
    FEATURE_DOCUMENT_CHECK,
    FEATURE_HOUSING_APPLICATION,
    FEATURE_NOTES_ANALYSIS,
    FEATURE_OPERATIONAL_SEARCH,
    FEATURE_REPORT_DRAFT,
    FEATURE_SUPPORT_PLANNING,
    FEATURE_TENANT_ASSISTANT,
)

# Controllable features not yet in the F3.3 cost catalogue constants.
FEATURE_DUPLICATE_DETECTION = "ai.agent.duplicate_detection"
FEATURE_AI_ACTIVITY = "ai.activity.transparency"

# Alias map so legacy/alternate IDs resolve to the registry key.
FEATURE_ALIASES: dict[str, str] = {
    "ai.agent.case_summary": FEATURE_CASE_SUMMARY,
    "ai.agent.document_check": FEATURE_DOCUMENT_CHECK,
    "ai.agent.support_plan_draft": FEATURE_SUPPORT_PLANNING,
    "ai.agent.operational_search": FEATURE_OPERATIONAL_SEARCH,
    "ai.agent.report_draft": FEATURE_REPORT_DRAFT,
    "ai.agent.duplicate_detection": FEATURE_DUPLICATE_DETECTION,
}


@dataclass(frozen=True)
class AiFeatureDefinition:
    feature_id: str
    name: str
    description: str
    phase_feature: str
    pilot_eligible: bool
    # When True, migration seeds existing orgs as enabled to preserve current access.
    preserve_enabled_for_existing_orgs: bool


REGISTRY: tuple[AiFeatureDefinition, ...] = (
    AiFeatureDefinition(
        FEATURE_NOTES_ANALYSIS,
        "Notes Analysis Agent",
        "Analyse daily support notes and suggest follow-ups for human review.",
        "F3.4",
        False,
        True,
    ),
    AiFeatureDefinition(
        FEATURE_CASE_SUMMARY,
        "Case Summaries",
        "Generate tenant case summaries from authorised records for human review.",
        "F3.5",
        False,
        True,
    ),
    AiFeatureDefinition(
        FEATURE_DOCUMENT_CHECK,
        "Smart Document Checker",
        "Check uploaded documents against organisation rules with human confirmation.",
        "F3.6",
        False,
        True,
    ),
    AiFeatureDefinition(
        FEATURE_SUPPORT_PLANNING,
        "Support Planning Agent",
        "Draft support-plan goals and milestones from authorised case data.",
        "F3.7",
        False,
        True,
    ),
    AiFeatureDefinition(
        FEATURE_HOUSING_APPLICATION,
        "Housing Application Agent",
        "Analyse housing applications for gaps and evidence checklist items.",
        "F3.8",
        False,
        True,
    ),
    AiFeatureDefinition(
        FEATURE_COMPLIANCE,
        "Compliance Agent",
        "Run compliance sweeps and explain findings for staff review.",
        "F3.9",
        False,
        True,
    ),
    AiFeatureDefinition(
        FEATURE_TENANT_ASSISTANT,
        "Tenant Assistant",
        "Tenant Q&A grounded only in organisation-approved content (pilot).",
        "F3.10",
        True,
        False,
    ),
    AiFeatureDefinition(
        FEATURE_DUPLICATE_DETECTION,
        "Duplicate Detection",
        "Search-first detection of potential duplicate people/applications.",
        "F3.11",
        False,
        True,
    ),
    AiFeatureDefinition(
        FEATURE_OPERATIONAL_SEARCH,
        "Natural-Language Operational Search",
        "Allowlisted natural-language search over authorised operational records.",
        "F3.12",
        False,
        True,
    ),
    AiFeatureDefinition(
        FEATURE_REPORT_DRAFT,
        "Weekly/Monthly Report Drafts",
        "Generate operational report drafts from authorised F2.14 metrics.",
        "F3.13",
        False,
        True,
    ),
    AiFeatureDefinition(
        FEATURE_AI_ACTIVITY,
        "AI Activity Transparency & Feedback",
        "View AI activity logs, sources/confidence metadata, and wrong-answer feedback.",
        "F3.14",
        False,
        True,
    ),
    AiFeatureDefinition(
        FEATURE_DAILY_LOG_REWRITE,
        "Daily Log Professional Rewrite",
        "Optional grammar and clarity rewrite of a draft daily note. Staff confirm the text before it is saved.",
        "F4.4",
        True,
        False,
    ),
)

REGISTRY_BY_ID: dict[str, AiFeatureDefinition] = {f.feature_id: f for f in REGISTRY}
CONTROLLABLE_FEATURE_IDS: frozenset[str] = frozenset(REGISTRY_BY_ID.keys())

# Platform infrastructure — never exposed as org toggles.
PLATFORM_INFRA_FEATURE_IDS: frozenset[str] = frozenset(
    {
        "ai.infra.foundation",
        "ai.infra.routing",
        "ai.infra.batch",
        "ai.infra.cache",
        "ai.infra.unattributed",
        "ai.budget",
        "ai.cost.dashboard",
    }
)


def canonical_feature_id(feature_id: str) -> str:
    return FEATURE_ALIASES.get(feature_id, feature_id)


def get_definition(feature_id: str) -> AiFeatureDefinition | None:
    return REGISTRY_BY_ID.get(canonical_feature_id(feature_id))


def is_registered(feature_id: str) -> bool:
    return canonical_feature_id(feature_id) in REGISTRY_BY_ID
