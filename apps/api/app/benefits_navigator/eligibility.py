"""Rule-based eligibility guidance engine — transparent, non-decisional."""

from __future__ import annotations

from typing import Any


def evaluate_rule(conditions: dict[str, Any], answers: dict[str, Any]) -> tuple[str, str]:
    required = conditions.get("required_fields") or []
    missing = [f for f in required if not answers.get(f)]
    if missing:
        return (
            "more_information_required",
            f"Missing information for published checks: {', '.join(missing)}. "
            "This is guidance only — not an official decision.",
        )

    geo = conditions.get("geographic_coverage")
    if geo and answers.get("local_authority"):
        allowed = geo if isinstance(geo, list) else [geo]
        if answers["local_authority"] not in allowed and "UK-wide" not in allowed:
            return (
                "unlikely_published_criteria",
                "Published geographic coverage may not include the local authority provided. Verify with the official source.",
            )

    category = conditions.get("category_slug")
    if category and answers.get("interest_category") and answers["interest_category"] != category:
        return (
            "information_needs_review",
            "Selected category may not match this programme — review official guidance.",
        )

    match_keys = conditions.get("match_any") or {}
    if match_keys:
        matched = any(str(answers.get(k)) == str(v) for k, v in match_keys.items() if answers.get(k) is not None)
        if not matched and match_keys:
            return (
                "unlikely_published_criteria",
                "Answers may not meet published criteria described in the source reference — confirm officially.",
            )

    return (
        "potentially_eligible",
        "Based on supplied answers and configured published conditions, you may wish to explore this programme. "
        "This is not a guarantee of eligibility.",
    )
