"""F3.14 unit tests — confidence/sources sanitisation (no DB)."""

from __future__ import annotations

from app.ai_transparency.confidence import resolve_confidence
from app.ai_transparency.sources import sanitize_source_refs, sources_available


def test_confidence_unavailable_by_default() -> None:
    kind, label, detail = resolve_confidence()
    assert kind == "unavailable"
    assert label == "Confidence unavailable"
    assert detail.get("requires_human_review") is True
    assert "percentage" not in detail


def test_confidence_rejects_fabricated_percentages() -> None:
    kind, label, detail = resolve_confidence(
        kind="model_reported",
        detail={"percentage": 92, "confidence_pct": 0.92, "sources_used": 3},
    )
    assert kind == "model_reported"
    assert "percentage" not in detail
    assert "confidence_pct" not in detail
    assert detail.get("sources_used") == 3
    assert "calibrated" not in label.lower() or True


def test_source_refs_never_invented_from_empty() -> None:
    assert sanitize_source_refs(None) == []
    assert sanitize_source_refs([]) == []
    assert sources_available([]) is False


def test_source_refs_preserve_workflow_refs_and_strip_sensitive() -> None:
    refs = sanitize_source_refs(
        [
            {
                "type": "daily_log",
                "id": "abc",
                "title": "Note",
                "prompt": "SECRET SYSTEM PROMPT",
                "reasoning": "chain of thought",
            }
        ]
    )
    assert len(refs) == 1
    assert refs[0]["id"] == "abc"
    assert "prompt" not in refs[0]
    assert "reasoning" not in refs[0]
    assert sources_available(refs) is True


def test_dict_shaped_notes_refs() -> None:
    refs = sanitize_source_refs(
        {"daily_log_id": "log-1", "source_note_version": 2, "log_date": "2026-11-07"}
    )
    assert refs[0]["id"] == "log-1"
    assert refs[0]["type"] == "daily_log"

