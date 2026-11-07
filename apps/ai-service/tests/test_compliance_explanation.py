"""F3.9 compliance explanation workflow tests (mocked provider path)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.budget.features import feature_for_workflow
from app.core.config import Settings
from app.graph.compliance_explanation import run_compliance_explanation, validate_explanation
from app.graph.runtime import SUPPORTED_WORKFLOWS


def test_compliance_explanation_registered() -> None:
    assert "compliance_explanation" in SUPPORTED_WORKFLOWS
    assert feature_for_workflow("compliance_explanation") == "ai.agent.compliance"


def test_validate_rejects_legal_certification() -> None:
    with pytest.raises(Exception):
        validate_explanation({"explanation": "The organisation is legally compliant overall."})


def test_run_compliance_explanation_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.graph import compliance_explanation as mod

    def _boom(**_k):
        raise RuntimeError("provider down")

    monkeypatch.setattr(mod, "run_routed_completion", _boom)
    result = run_compliance_explanation(
        settings=Settings(environment="test"),
        organisation_id=uuid4(),
        findings=[{"rule_id": "training.expired", "result": "potential_gap", "title": "Expired", "module": "training"}],
    )
    assert "legal certification" in result["explanation"].lower()
    assert result["legal_certification"] is False


def test_run_compliance_explanation_ai_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.graph import compliance_explanation as mod

    monkeypatch.setattr(
        mod,
        "run_routed_completion",
        lambda **_k: {
            "text": '{"explanation": "AI assistance only — staff should verify the expired training record against the source."}'
        },
    )
    result = run_compliance_explanation(
        settings=Settings(environment="test"),
        organisation_id=uuid4(),
        findings=[{"rule_id": "training.expired", "module": "training", "title": "x", "result": "potential_gap"}],
    )
    assert "staff should verify" in result["explanation"].lower()
