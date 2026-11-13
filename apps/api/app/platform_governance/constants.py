"""F8.12 governance constants."""

from __future__ import annotations

COMPLIANCE_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("data_protection", "Data protection"),
    ("safeguarding", "Safeguarding"),
    ("financial", "Financial records"),
    ("hsl", "Health and safety"),
    ("staff_training", "Staff training"),
    ("tenancy", "Tenancy management"),
)

INCIDENT_SEVERITIES: tuple[str, ...] = ("low", "medium", "high", "critical")

ADDON_DISCLAIMER = (
    "Governance tools assist administration; they do not guarantee legal compliance. Configure policies per organisation and jurisdiction."
)

AI_NOTICE = "[AI-generated summary — requires human review]"
