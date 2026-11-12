"""F7.2 privacy management constants — statuses are technical, not legal approvals."""

from __future__ import annotations

DPIA_STATUSES = frozenset(
    {
        "not_started",
        "in_progress",
        "pending_approval",
        "approved",
        "rejected",
        "review_required",
    }
)

DSR_STATUSES = frozenset(
    {
        "registered",
        "in_review",
        "awaiting_authorised_decision",
        "completed",
        "rejected",
        "cancelled",
    }
)

DSR_CATEGORIES = frozenset(
    {
        "access",
        "rectification",
        "erasure",
        "restrict_processing",
        "portability",
        "object",
        "other",
    }
)

RETENTION_POLICY_STATUSES = frozenset({"draft", "pending_approval", "active", "superseded"})

RISK_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
RISK_STATUSES = frozenset({"open", "mitigating", "mitigated", "accepted", "closed"})
