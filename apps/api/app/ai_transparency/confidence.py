"""Confidence semantics for F3.14.

Important: model self-reported certainty is NOT a calibrated probability.
We never invent percentages. Default display is "Confidence unavailable".
"""

from __future__ import annotations

from typing import Any

CONFIDENCE_KINDS = frozenset(
    {
        "unavailable",
        "retrieval_coverage",
        "deterministic_validation",
        "human_reviewed",
        "model_reported",
    }
)

LABELS = {
    "unavailable": "Confidence unavailable",
    "retrieval_coverage": "Based on retrieved sources (not a calibrated accuracy score)",
    "deterministic_validation": "Deterministic validation result (not model confidence)",
    "human_reviewed": "Human review status (not model confidence)",
    "model_reported": "Model-reported signal (not calibrated; requires human review)",
}

# Forbidden keys that would imply fabricated calibrated percentages.
_FORBIDDEN_DETAIL_KEYS = frozenset(
    {
        "percentage",
        "percent",
        "probability",
        "calibrated_score",
        "accuracy",
        "confidence_pct",
        "confidence_percent",
    }
)


def resolve_confidence(
    *,
    kind: str | None = None,
    detail: dict[str, Any] | None = None,
    label_override: str | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """Return (kind, label, sanitized_detail). Never fabricates scores."""
    resolved = (kind or "unavailable").strip().lower()
    if resolved not in CONFIDENCE_KINDS:
        resolved = "unavailable"
    safe_detail: dict[str, Any] = {}
    for key, value in (detail or {}).items():
        if key.lower() in _FORBIDDEN_DETAIL_KEYS:
            continue
        if isinstance(value, (str, int, bool, float)) and key.lower() not in {
            "score",
            "pct",
        }:
            # Allow non-percentage numeric counts (e.g. sources_used) only.
            if isinstance(value, float) and 0 <= value <= 1 and "coverage" not in key.lower():
                continue
            safe_detail[str(key)[:64]] = value
        elif isinstance(value, list) and len(value) <= 20:
            safe_detail[str(key)[:64]] = [str(v)[:128] for v in value[:20]]
    label = (label_override or LABELS[resolved])[:255]
    if resolved == "unavailable":
        safe_detail.setdefault(
            "requires_human_review",
            True,
        )
        safe_detail.setdefault(
            "note",
            "No calibrated confidence signal is available for this result.",
        )
    return resolved, label, safe_detail
