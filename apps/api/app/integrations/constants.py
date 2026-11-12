"""Integration hub constants and provider registry catalog."""

from __future__ import annotations

CATEGORIES = frozenset({"council", "hr", "finance", "community_service"})
AUTH_TYPES = frozenset({"api_key", "bearer", "oauth2", "none"})
CONNECTION_STATUSES = frozenset(
    {"not_configured", "configured", "connected", "failed", "disabled"}
)
SYNC_DIRECTIONS = frozenset({"import", "export", "bidirectional", "health_check"})

# Catalog of stub provider adapters (foundation only — not live partner links)
PROVIDER_CATALOG: dict[str, dict[str, str]] = {
    "council_generic": {
        "provider_name": "Council API (generic)",
        "category": "council",
        "description": "Foundation adapter for future council case/referral APIs.",
    },
    "hr_generic": {
        "provider_name": "HR API (generic)",
        "category": "hr",
        "description": "Foundation adapter for future HR rostering/staff APIs.",
    },
    "finance_generic": {
        "provider_name": "Finance API (generic)",
        "category": "finance",
        "description": "Foundation adapter for future finance ledger APIs.",
    },
    "community_service_generic": {
        "provider_name": "Community / local services API (generic)",
        "category": "community_service",
        "description": "Foundation adapter for future community service directories.",
    },
}

ALLOWED_DATA_TYPES = frozenset({"string", "integer", "number", "boolean", "date", "datetime", "uuid"})
