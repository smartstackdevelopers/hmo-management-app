from __future__ import annotations

from app.prompts.store import PromptStore

FOUNDATION_PROMPT_ID = "hmore.foundation.echo"
FOUNDATION_PROMPT_VERSION = "1.0.0"
NOTES_ANALYSIS_PROMPT_ID = "hmore.notes_analysis.v1"
NOTES_ANALYSIS_PROMPT_VERSION = "1.0.0"
CASE_SUMMARY_PROMPT_ID = "hmore.case_summary.v1"
CASE_SUMMARY_PROMPT_VERSION = "1.0.0"


def seed_prompts(store: PromptStore) -> None:
    store.upsert_draft(
        prompt_id=FOUNDATION_PROMPT_ID,
        version=FOUNDATION_PROMPT_VERSION,
        workflow_or_feature="foundation_echo",
        template=(
            "You are the HMore foundation echo workflow. "
            "Organisation={{organisation_id}} Role={{role}}. "
            "Echo the safe operational message only: {{message}}"
        ),
        metadata={"phase": "F3.1", "agent": None},
    )
    store.publish(FOUNDATION_PROMPT_ID, FOUNDATION_PROMPT_VERSION)

    store.upsert_draft(
        prompt_id=NOTES_ANALYSIS_PROMPT_ID,
        version=NOTES_ANALYSIS_PROMPT_VERSION,
        workflow_or_feature="notes_analysis",
        template=(
            "You are the HMore Notes Analysis assistant for organisation {{organisation_id}}. "
            "Analyse ONLY the authorised daily note JSON provided. "
            "Do not invent facts, diagnoses, housing decisions, or risk classifications. "
            "Return a single JSON object with keys: summary (string), key_observations (string array), "
            "missing_details (array of {title,body,rationale,source_excerpt,is_interpretation}), "
            "suggested_actions (array of {title,body,rationale,source_excerpt,is_interpretation}), "
            "uncertainty_notes (string or null). "
            "Label interpretations clearly. Missing details are suggestions for human review, "
            "not compliance failures. Note JSON: {{note_json}}"
        ),
        metadata={"phase": "F3.4", "agent": "notes_analysis"},
    )
    store.publish(NOTES_ANALYSIS_PROMPT_ID, NOTES_ANALYSIS_PROMPT_VERSION)

    store.upsert_draft(
        prompt_id=CASE_SUMMARY_PROMPT_ID,
        version=CASE_SUMMARY_PROMPT_VERSION,
        workflow_or_feature="case_summary",
        template=(
            "You are the HMore case summary assistant for organisation {{organisation_id}}. "
            "Use ONLY the authorised case packet JSON. Do not invent facts, dates, names, "
            "diagnoses, safeguarding conclusions, legal findings, or risk classifications. "
            "Return one JSON object with keys: sections (object with overview, background, "
            "events, recent_support, needs_and_goals, outstanding_actions, upcoming), "
            "missing_information (string array), recorded_concerns (array of "
            "{text, source_type, source_id, explicitly_recorded} where source_id is copied "
            "from the packet and explicitly_recorded is true), covered_from, covered_to, "
            "uncertainty_notes. Label the text as AI-generated. Packet JSON: {{packet_json}}"
        ),
        metadata={"phase": "F3.5", "workflow": "case_summary"},
    )
    store.publish(CASE_SUMMARY_PROMPT_ID, CASE_SUMMARY_PROMPT_VERSION)
