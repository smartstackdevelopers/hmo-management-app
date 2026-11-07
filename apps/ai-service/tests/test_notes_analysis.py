"""F3.4 notes analysis workflow unit tests (mocked / heuristic — not real LLM billing)."""

from __future__ import annotations

from uuid import uuid4

from app.core.config import Settings
from app.graph.notes_analysis import (
    heuristic_notes_analysis,
    run_notes_analysis,
    validate_notes_analysis_output,
)
from app.graph.runtime import SUPPORTED_WORKFLOWS, execute_workflow
from app.context.trusted import TrustedCallerContext
from app.budget.features import feature_for_workflow


def test_notes_analysis_workflow_registered() -> None:
    assert "notes_analysis" in SUPPORTED_WORKFLOWS
    assert feature_for_workflow("notes_analysis") == "ai.agent.notes_analysis"


def test_schema_validation_rejects_empty_summary() -> None:
    import pytest

    with pytest.raises(Exception):
        validate_notes_analysis_output({"summary": "", "key_observations": []})


def test_heuristic_grounded() -> None:
    out = heuristic_notes_analysis(
        {
            "summary": "Call",
            "notes": "No outcome recorded for the activity discussed.",
            "follow_up_required": True,
            "next_action": "",
            "log_date": "2026-11-07",
            "activity_category": "support",
        }
    )
    assert out.generation_method == "structured_heuristic"
    assert out.missing_details


def test_run_notes_analysis_without_llm() -> None:
    settings = Settings(LLM_PROVIDER="none", AI_BUDGET_ENFORCEMENT_FAIL_OPEN=True)
    result = run_notes_analysis(
        settings=settings,
        organisation_id=uuid4(),
        note_payload={
            "summary": "Visit",
            "notes": "Tenant wants warehouse work.",
            "follow_up_required": False,
            "activity_category": "support",
            "log_date": "2026-11-07",
        },
    )
    assert result["generation_method"] == "structured_heuristic"
    assert result["analysis"]["summary"]


def test_execute_workflow_notes_analysis() -> None:
    settings = Settings(LLM_PROVIDER="none", AI_BUDGET_ENFORCEMENT_FAIL_OPEN=True, AI_SERVICE_TOKEN="t")
    ctx = TrustedCallerContext(
        organisation_id=uuid4(),
        user_id=uuid4(),
        role="support_worker",
        features=frozenset({"ai.workflow.execute"}),
    )
    out = execute_workflow(
        workflow_id="notes_analysis",
        ctx=ctx,
        settings=settings,
        input_payload={
            "note": {
                "summary": "Check-in",
                "notes": "Discussed CV. Meeting planned.",
                "follow_up_required": True,
                "next_action": "",
                "activity_category": "support",
                "log_date": "2026-11-07",
            }
        },
    )
    assert out["status"] == "completed"
    assert out["requires_approval"] is True
    assert out["result"]["analysis"]["summary"]
