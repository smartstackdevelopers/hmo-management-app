"""F6.1 constants."""

from __future__ import annotations

RENT_STATUSES = ("due", "outstanding", "recorded_paid", "waived", "cancelled")
INSPECTION_STATUSES = ("scheduled", "in_progress", "completed", "cancelled")
OPEN_REPAIR_STATUSES = (
    "submitted",
    "acknowledged",
    "under_review",
    "awaiting_approval",
    "approved",
    "assigned",
    "scheduled",
    "in_progress",
    "awaiting_parts",
    "on_hold",
)
COMPLETED_REPAIR_STATUSES = ("completed", "closed")
LEDGER_DISCLAIMER = (
    "This is a rent records ledger only. HMore does not process online rent payments or banking transfers here."
)
