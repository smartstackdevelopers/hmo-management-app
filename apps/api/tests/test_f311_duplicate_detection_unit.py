"""F3.11 unit tests — normalisation and match strength rules (no DB, no AI)."""

from __future__ import annotations

import uuid

from app.duplicate_detection.matching import MatchHit, NAME_SIMILARITY_THRESHOLD, _name_similarity
from app.duplicate_detection.normalize import (
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_reference,
)
from app.duplicate_detection.service import NOTICE


def test_notice_requires_human_review_and_no_auto_merge() -> None:
    assert "Potential Duplicates — Human Review Required" in NOTICE
    assert "never deletes or merges" in NOTICE.lower()


def test_normalize_email_and_name_case_insensitive() -> None:
    assert normalize_email("  Alice@Example.COM ") == "alice@example.com"
    assert normalize_name("  José  García ") == "jose garcia"
    assert normalize_name(None) is None
    assert normalize_email("") is None


def test_normalize_phone_keeps_digits_and_rejects_short() -> None:
    assert normalize_phone("+44 7700 900123") == "447700900123"
    assert normalize_phone("123") is None
    assert normalize_phone(None) is None


def test_normalize_reference_strips_punctuation_safely() -> None:
    assert normalize_reference("TEN-001/A") == "ten001a"
    assert normalize_reference("  ") is None


def test_name_similarity_threshold_does_not_prove_identity() -> None:
    score = _name_similarity("Alice Smith", "Alice Smyth")
    assert score is not None
    assert 0.0 < score <= 1.0
    # Near-identical names alone stay below automatic identity — callers use "possible".
    assert NAME_SIMILARITY_THRESHOLD >= 0.8


def test_match_hit_dedupe_key_is_order_independent() -> None:
    a = uuid.uuid4()
    b = uuid.uuid4()
    left = MatchHit("tenant", a, b, "exact", 1.0, ["email"], ["Exact"])
    right = MatchHit("tenant", b, a, "exact", 1.0, ["email"], ["Exact"])
    assert left.dedupe_key() == right.dedupe_key()
    assert left.ordered_ids() == right.ordered_ids()
