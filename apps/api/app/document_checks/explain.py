"""Explain rule findings without inventing document facts. Not a live model call."""

from __future__ import annotations

from typing import Any


def explain_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations = []
    for item in findings:
        if item.get("outcome") not in {"fail", "warning", "not_performed"}:
            continue
        observations.append(
            {
                "title": item.get("title") or item.get("code"),
                "body": (
                    "Explanation of a recorded check, not a new fact. "
                    + str(item.get("detail") or "")
                )[:1500],
                "source_finding_code": item.get("code"),
                "needs_human_verification": bool(item.get("needs_human_verification")),
                "origin": "structured_heuristic",
            }
        )
    return observations


def validate_ai_observations(payload: dict[str, Any], findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = {item.get("code") for item in findings}
    raw = payload.get("observations")
    if not isinstance(raw, list):
        raise ValueError("observations")
    cleaned = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("observation")
        code = item.get("source_finding_code")
        if code not in allowed:
            raise ValueError("untraceable")
        body = str(item.get("body") or "").strip()
        title = str(item.get("title") or "").strip()
        if not body or not title:
            raise ValueError("empty")
        lowered = body.lower()
        if "document is approved" in lowered or "document is valid" in lowered or "eligible" in lowered:
            raise ValueError("decision")
        cleaned.append(
            {
                "title": title[:200],
                "body": body[:1500],
                "source_finding_code": code,
                "needs_human_verification": True,
                "origin": "llm",
            }
        )
    return cleaned
