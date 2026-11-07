"""Report draft narrative from aggregated metrics only. Never invents numbers."""

from __future__ import annotations

from typing import Any


def run_report_draft_narrative(*, period_type: str, metrics: dict[str, Any]) -> dict[str, Any]:
    sections = metrics.get("sections") or {}
    unavailable = metrics.get("unavailable") or []
    lines = [
        "AI-GENERATED DRAFT — REQUIRES HUMAN REVIEW",
        f"Period type: {period_type}",
        f"Period: {metrics.get('period_start')} to {metrics.get('period_end')}",
        "The figures below are copied from deterministic reporting summaries. Do not treat this narrative as an approved operational decision.",
    ]
    for name, section in sections.items():
        lines.append(f"Section {name}: {section}")
    if unavailable:
        lines.append(f"Unavailable sections for this requester: {', '.join(unavailable)}")
    if not sections:
        lines.append("No authorised reporting sections were available for this period.")
    return {
        "narrative": "\n".join(lines)[:8000],
        "prompt_id": "report_draft_narrative",
        "prompt_version": "1",
        "provider": "deterministic",
        "model_id": "metrics-echo",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cache_status": "miss",
        "invented_metrics": False,
    }
