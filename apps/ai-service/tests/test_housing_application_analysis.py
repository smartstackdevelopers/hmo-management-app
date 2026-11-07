"""F3.8 housing analysis workflow. Heuristic only — not a live model call."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.budget.features import feature_for_workflow
from app.context.trusted import TrustedCallerContext
from app.core.config import Settings
from app.core.errors import WorkflowError
from app.graph.housing_application_analysis import run_housing_application_analysis, validate_analysis
from app.graph.runtime import SUPPORTED_WORKFLOWS, execute_workflow


def test_housing_application_analysis_registered() -> None:
    assert "housing_application_analysis" in SUPPORTED_WORKFLOWS
    assert feature_for_workflow("housing_application_analysis") == "ai.agent.housing_application"


def test_decision_language_rejected() -> None:
    with pytest.raises(WorkflowError):
        validate_analysis({"gap_narrative": "The application is approved for housing allocation."})


def test_heuristic_does_not_approve() -> None:
    result = run_housing_application_analysis(
        settings=Settings(LLM_PROVIDER="none", AI_BUDGET_ENFORCEMENT_FAIL_OPEN=True, AI_SERVICE_TOKEN="t"),
        organisation_id=uuid4(),
        findings=[{"code": "evidence_missing", "outcome": "missing", "title": "Proof of identity"}],
        application_reference="APP-9",
    )
    body = result["analysis"]["gap_narrative"].lower()
    assert "approved" not in body
    assert "eligible" not in body
    assert result["generation_method"] == "structured_heuristic"


def test_execute_workflow_requires_approval() -> None:
    settings = Settings(LLM_PROVIDER="none", AI_BUDGET_ENFORCEMENT_FAIL_OPEN=True, AI_SERVICE_TOKEN="t")
    ctx = TrustedCallerContext(
        organisation_id=uuid4(),
        user_id=uuid4(),
        role="organisation_admin",
        features=frozenset({"ai.workflow.execute"}),
    )
    out = execute_workflow(
        workflow_id="housing_application_analysis",
        ctx=ctx,
        settings=settings,
        input_payload={
            "findings": [{"code": "household_summary_blank", "outcome": "incomplete", "title": "Household summary"}],
            "application_reference": "APP-1",
        },
    )
    assert out["status"] == "completed"
    assert out["requires_approval"] is True
    assert out["result"]["generation_method"] == "structured_heuristic"
