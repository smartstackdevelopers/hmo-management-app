"""F3.9 unit tests — rules catalog and AI safety (no DB)."""

from __future__ import annotations

import pytest

from app.compliance_agent.rules import (
    NOTICE,
    get_rule,
    heuristic_explanation,
    list_rules,
    validate_ai_explanation,
)


def test_rules_are_traceable_to_hmore_sources() -> None:
    rules = list_rules()
    assert len(rules) >= 6
    for rule in rules:
        assert rule.source.startswith("hmore.")
        assert rule.version
        assert rule.module


def test_training_rule_source() -> None:
    rule = get_rule("training.expired")
    assert rule is not None
    assert "f23" in rule.source


def test_narrative_rejects_legal_certification() -> None:
    with pytest.raises(ValueError):
        validate_ai_explanation("The organisation is legally compliant with all housing law.")
    with pytest.raises(ValueError):
        validate_ai_explanation("This confirms a statutory breach and regulatory violation confirmed.")


def test_heuristic_explanation_is_safe() -> None:
    text = heuristic_explanation([])
    assert "does not provide legal certification" in text.lower() or NOTICE.split("—")[0] in text
    assert "legally compliant" not in text.lower()

