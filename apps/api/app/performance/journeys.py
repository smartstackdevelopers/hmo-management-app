"""Critical journey probes for F7.4 (synthetic / smoke timings)."""

from __future__ import annotations

from dataclasses import dataclass
from starlette.testclient import TestClient


@dataclass(frozen=True)
class JourneyProbe:
    key: str
    category: str
    description: str
    method: str
    path: str


# Paths chosen for safe, non-destructive smoke (auth may return 401 — still measures middleware stack).
CRITICAL_JOURNEY_PROBES: tuple[JourneyProbe, ...] = (
    JourneyProbe("auth.session_gate", "A", "Unauthenticated API gate", "GET", "/api/v1/isolation/properties"),
    JourneyProbe("tenant.management_gate", "B", "Tenant API auth gate", "GET", "/api/v1/tenants"),
    JourneyProbe("housing.applications_gate", "C", "Housing API auth gate", "GET", "/api/v1/housing-applications"),
    JourneyProbe("staff.caseload_gate", "D", "Support caseload auth gate", "GET", "/api/v1/caseload"),
    JourneyProbe("support.plans_gate", "E", "Support plans dashboard auth gate", "GET", "/api/v1/support-plans/dashboard"),
    JourneyProbe("maintenance.requests_gate", "F", "Maintenance list auth gate", "GET", "/api/v1/maintenance"),
    JourneyProbe("reports.dashboard_gate", "G", "Reporting auth gate", "GET", "/api/v1/reports/dashboard"),
    JourneyProbe("landlord.enterprise_gate", "H", "Landlord enterprise auth gate", "GET", "/api/v1/landlord-enterprise/portfolio"),
    JourneyProbe("automation.rules_gate", "I", "Automation auth gate", "GET", "/api/v1/automation/rules"),
    JourneyProbe("ai.activity_gate", "J", "AI activity auth gate", "GET", "/api/v1/ai-activity"),
    JourneyProbe("privacy.dashboard_gate", "F7.2", "Privacy dashboard auth gate", "GET", "/api/v1/privacy/dashboard"),
    JourneyProbe("backup.dashboard_gate", "F7.3", "Backup dashboard auth gate", "GET", "/api/v1/backups/dashboard"),
    JourneyProbe("health.liveness", "Platform", "API liveness", "GET", "/health"),
    JourneyProbe("health.v1", "Platform", "API v1 health", "GET", "/api/v1/health"),
)


def run_probe(client: TestClient, probe: JourneyProbe) -> tuple[int, float]:
    """Returns (status_code, elapsed_ms)."""
    import time

    t0 = time.perf_counter()
    if probe.method == "GET":
        response = client.get(probe.path)
    else:
        response = client.request(probe.method, probe.path)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return response.status_code, elapsed_ms
