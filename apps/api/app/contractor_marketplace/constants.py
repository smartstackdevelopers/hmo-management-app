"""F8.5 contractor marketplace constants."""

from __future__ import annotations

DEFAULT_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("plumbing", "Plumbing"),
    ("electrical", "Electrical"),
    ("heating_gas", "Heating and Gas"),
    ("roofing", "Roofing"),
    ("painting_decorating", "Painting and Decorating"),
    ("cleaning", "Cleaning"),
    ("general_repairs", "General Repairs"),
    ("fire_safety", "Fire Safety"),
    ("property_inspection", "Property Inspection"),
    ("other", "Other Approved Services"),
)

ADDON_DISCLAIMER = (
    "Contractors are listed only after authorised verification. HMore does not invent certifications or insurance status."
)
