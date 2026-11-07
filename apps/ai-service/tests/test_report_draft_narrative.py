from app.budget.features import feature_for_workflow
from app.graph.report_draft_narrative import run_report_draft_narrative
from app.graph.runtime import SUPPORTED_WORKFLOWS


def test_report_draft_workflow_registered() -> None:
    assert "report_draft_narrative" in SUPPORTED_WORKFLOWS
    assert feature_for_workflow("report_draft_narrative") == "ai.workflow.report_draft"


def test_narrative_does_not_invent_metrics() -> None:
    result = run_report_draft_narrative(
        period_type="weekly",
        metrics={
            "period_start": "a",
            "period_end": "b",
            "sections": {"housing": {"total": 2}},
            "unavailable": [],
        },
    )
    assert result["invented_metrics"] is False
    assert "REQUIRES HUMAN REVIEW" in result["narrative"]
    assert "total': 2" in result["narrative"] or "total\": 2" in result["narrative"] or "2" in result["narrative"]
