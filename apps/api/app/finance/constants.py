"""F6.6 finance constants."""

from __future__ import annotations

RECORD_TYPES = frozenset({"income", "expense", "other"})
RECORD_STATUSES = frozenset({"draft", "posted", "voided"})
BUDGET_STATUSES = frozenset({"draft", "active", "closed"})

DEFAULT_CATEGORIES: dict[str, str] = {
    "rent_income": "Rent income",
    "other_income": "Other income",
    "maintenance": "Maintenance",
    "utilities": "Utilities",
    "staffing": "Staffing",
    "compliance": "Compliance",
    "admin": "Administration",
    "other_expense": "Other expense",
}

FINANCE_DISCLAIMER = (
    "Finance & Budgets is an authorised records and reporting module. "
    "HMore does not process online payments, banking transfers, or payment gateways here. "
    "Amounts are ledger entries only; 'recorded' does not mean bank-verified settlement."
)
