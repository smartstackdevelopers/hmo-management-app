"""F8.3 rent payment constants."""

from __future__ import annotations

PAYMENT_STATUSES = frozenset(
    {"pending", "due", "partially_paid", "paid", "overdue", "disputed", "cancelled"}
)

PAYMENT_METHODS = frozenset({"bank_transfer", "direct_debit", "card", "cash", "other"})

ADDON_DISCLAIMER = (
    "F8.3 payments add-on: manual entries are not verified until authorised. "
    "Gateway payments use provider test mode unless explicitly approved for live processing."
)
