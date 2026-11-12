"""F6.7 Council Portal constants."""

from __future__ import annotations

ADDON_ROLE_LABEL = "council_officer"
OFFICER_STATUSES = frozenset({"invited", "active", "suspended", "revoked"})
SHARE_STATUSES = frozenset({"active", "revoked", "expired"})
ALLOWED_SCOPES = frozenset(
    {
        "application_status",
        "evidence_meta",
        "approval_history",
        "reports_summary",
    }
)

PORTAL_DISCLAIMER = (
    "Council Portal is an optional Section 11 add-on. Council officers are not a core HMore role. "
    "Access is limited to applications explicitly shared by the organisation. "
    "Tenant caseload, private notes, and unshared records are never exposed."
)
