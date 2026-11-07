"""F3.10 tenant assistant workflow tests (mocked provider)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.budget.features import feature_for_workflow
from app.core.config import Settings
from app.graph.runtime import SUPPORTED_WORKFLOWS
from app.graph.tenant_assistant import run_tenant_assistant, validate_output


def test_tenant_assistant_registered() -> None:
    assert "tenant_assistant" in SUPPORTED_WORKFLOWS
    assert feature_for_workflow("tenant_assistant") == "ai.agent.tenant_assistant"


def test_validate_rejects_decisions() -> None:
    with pytest.raises(Exception):
        validate_output({"answer": "You are eligible and the application is approved today.", "grounded": True})


def test_heuristic_without_snippets() -> None:
    result = run_tenant_assistant(
        settings=Settings(environment="test"),
        organisation_id=uuid4(),
        question="What is the policy?",
        approved_snippets=[],
    )
    # Force heuristic by empty provider path via monkeypatch in next test; empty snippets still OK via try path
    assert result["makes_official_decisions"] is False


def test_run_falls_back_when_provider_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.graph import tenant_assistant as mod

    monkeypatch.setattr(mod, "run_routed_completion", lambda **_k: (_ for _ in ()).throw(RuntimeError("down")))
    result = run_tenant_assistant(
        settings=Settings(environment="test"),
        organisation_id=uuid4(),
        question="Where is the fire assembly point?",
        approved_snippets=[
            {
                "content_id": "1",
                "title": "Fire assembly point",
                "body": "Assemble at the car park.",
                "source_type": "maintenance_emergency_content",
            }
        ],
    )
    assert "car park" in result["answer"].lower() or "approved" in result["answer"].lower()
    assert result["makes_official_decisions"] is False
