"""F8.4 LMS constants."""

from __future__ import annotations

DEFAULT_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("safeguarding", "Safeguarding Training"),
    ("gdpr", "GDPR and Data Protection"),
    ("health_safety", "Health and Safety"),
    ("fire_safety", "Fire Safety"),
    ("equality_diversity", "Equality and Diversity"),
    ("tenant_support", "Tenant Support"),
    ("housing_management", "Housing Management"),
    ("maintenance_safety", "Maintenance and Property Safety"),
    ("ai_digital", "AI and Digital Skills"),
    ("professional_dev", "Staff Professional Development"),
)

COURSE_STATUSES = frozenset({"draft", "published", "archived"})
CERTIFICATE_STATUSES = frozenset({"issued", "valid", "expired", "revoked"})
ADDON_DISCLAIMER = (
    "HMore LMS certificates indicate course completion within your organisation. "
    "They are not external accreditation unless your organisation has verified accreditation."
)
