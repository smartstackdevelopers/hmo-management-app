"""F3.12 AI service: interpretation returns a spec and never SQL."""

from app.budget.features import feature_for_workflow
from app.graph.operational_search import interpret_question, run_operational_search
from app.graph.runtime import SUPPORTED_WORKFLOWS


def test_operational_search_registered() -> None:
    assert "operational_search" in SUPPORTED_WORKFLOWS
    assert feature_for_workflow("operational_search") == "ai.workflow.operational_search"


def test_interpretation_has_no_sql() -> None:
    result = run_operational_search(question="Show overdue maintenance requests")
    assert result["executed_sql"] is False
    assert "sql" not in result["specification"]
    assert result["specification"]["entity"] == "maintenance_request"
    blocked = interpret_question("please execute drop table tenants")
    assert blocked["outcome"] == "unsupported"
