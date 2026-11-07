"""F3.5 case summary workflow tests.

These use the structured heuristic or schema checks. They do not call a real LLM provider.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.budget.features import feature_for_workflow
from app.context.trusted import TrustedCallerContext
from app.core.config import Settings
from app.core.errors import WorkflowError
from app.graph.case_summary import grounded_case_summary, run_case_summary, validate_case_summary_output
from app.graph.runtime import SUPPORTED_WORKFLOWS, execute_workflow


def _packet() -> dict:
    return {
        "profile": {"id": "t1", "preferred_name": "Amina", "status": "active", "tenancy_reference": "T-1"},
        "daily_notes": [],
        "meetings": [],
        "appointments": [],
        "follow_ups": [],
        "support_plans": [],
        "goals": [],
        "incidents": [],
        "complaints": [],
        "maintenance": [],
        "documents": [],
        "sources": [{"type": "tenant", "id": "t1"}],
    }


def test_case_summary_registered() -> None:
    assert "case_summary" in SUPPORTED_WORKFLOWS
    assert feature_for_workflow("case_summary") == "ai.workflow.case_summaries"


def test_invalid_output_is_rejected() -> None:
    with pytest.raises(WorkflowError):
        validate_case_summary_output({"sections": {"overview": ""}}, _packet())
    with pytest.raises(WorkflowError):
        validate_case_summary_output(
            {
                "sections": {
                    "overview": "x",
                    "background": "x",
                    "events": "x",
                    "recent_support": "x",
                    "needs_and_goals": "x",
                    "outstanding_actions": "x",
                    "upcoming": "x",
                },
                "recorded_concerns": [
                    {
                        "text": "Invented concern",
                        "source_type": "incident",
                        "source_id": "missing",
                        "explicitly_recorded": True,
                    }
                ],
            },
            _packet(),
        )


def test_heuristic_and_execute_without_provider() -> None:
    grounded = grounded_case_summary(_packet())
    assert "Amina" in grounded["sections"]["overview"]
    assert grounded["generation_method"] == "structured_heuristic"
    settings = Settings(LLM_PROVIDER="none", AI_BUDGET_ENFORCEMENT_FAIL_OPEN=True, AI_SERVICE_TOKEN="t")
    result = run_case_summary(settings=settings, organisation_id=uuid4(), packet=_packet())
    assert result["generation_method"] == "structured_heuristic"
    assert result["prompt_id"] == "hmore.case_summary.v1"
    ctx = TrustedCallerContext(
        organisation_id=uuid4(),
        user_id=uuid4(),
        role="organisation_admin",
        features=frozenset({"ai.workflow.execute"}),
    )
    out = execute_workflow(
        workflow_id="case_summary",
        ctx=ctx,
        settings=settings,
        input_payload={"packet": _packet()},
    )
    assert out["status"] == "completed"
    assert out["requires_approval"] is True
    assert out["result"]["summary"]["sections"]["overview"]
