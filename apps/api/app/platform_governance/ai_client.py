"""F8.12 AI summaries for administrators."""

from __future__ import annotations

from typing import Any


def summarize_admin_activity(*, enabled: bool, audit_snippets: list[str]) -> dict[str, Any]:
    if not enabled:
        return {"summary": "Enable AI assistant in governance settings for summaries."}
    joined = " ".join(audit_snippets[:5])
    return {
        "summary": (
            f"Recent activity includes {len(audit_snippets)} sampled events. "
            f"Highlights: {(joined[:200] + '…') if len(joined) > 200 else joined or 'none recorded'}."
        ),
        "provider": "sandbox",
    }
