"""F8.7 benefits navigator constants."""

from __future__ import annotations

DEFAULT_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("housing_benefits", "Housing Benefits"),
    ("universal_credit", "Universal Credit"),
    ("council_tax_support", "Council Tax Support"),
    ("employment_support", "Employment Support"),
    ("disability_benefits", "Disability-related Benefits"),
    ("carer_support", "Carer Support"),
    ("food_assistance", "Food Assistance"),
    ("energy_utility_support", "Energy and Utility Support"),
    ("emergency_financial", "Emergency Financial Assistance"),
    ("local_community", "Local Community Support"),
)

ASSESSMENT_STATUSES = frozenset(
    {
        "potentially_eligible",
        "more_information_required",
        "unlikely_published_criteria",
        "information_needs_review",
    }
)

DEFAULT_CHECKLIST_ITEMS: tuple[str, ...] = (
    "identity_evidence",
    "housing_evidence",
    "income_evidence",
    "employment_evidence",
    "bank_statements",
    "supporting_documents",
)

AI_NOTICE = (
    "Guidance only — not an official eligibility decision. Always confirm with the published source "
    "or a qualified adviser."
)

ADDON_DISCLAIMER = (
    "Benefits information must be verified by authorised administrators. HMore does not guarantee eligibility "
    "or submit government applications."
)
