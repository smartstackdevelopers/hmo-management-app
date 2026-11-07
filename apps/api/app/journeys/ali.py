"""Ali Hassan journey — authoritative steps from HMore implementation plan F2.15.

Scenario (proposal-aligned, synthetic data only):
manual daily note → repair request → organisation admin approval → maintenance progression.

No AI services are invoked in this journey definition or its automated verifier.
"""

from __future__ import annotations

from typing import TypedDict


class JourneyStep(TypedDict):
    order: int
    actor_role: str
    module: str
    action: str
    service_or_api: str


ALI_JOURNEY_ID = "ali_hassan_water_leak_v1"

ALI_JOURNEY_STEPS: list[JourneyStep] = [
    {
        "order": 1,
        "actor_role": "organisation_admin",
        "module": "F2.1",
        "action": "Assign Support Worker to tenant caseload",
        "service_or_api": "support.create_assignment",
    },
    {
        "order": 2,
        "actor_role": "support_worker",
        "module": "F2.1",
        "action": "Create daily log noting water leak under sink",
        "service_or_api": "support.create_daily_log",
    },
    {
        "order": 3,
        "actor_role": "support_worker",
        "module": "F2.8",
        "action": "Raise maintenance request (requires_approval)",
        "service_or_api": "maintenance.create_request",
    },
    {
        "order": 4,
        "actor_role": "organisation_admin",
        "module": "F2.8 / F2.13",
        "action": "Approve maintenance awaiting_approval",
        "service_or_api": "maintenance.record_approval",
    },
    {
        "order": 5,
        "actor_role": "organisation_admin",
        "module": "F2.13",
        "action": "Approvals inbox lists maintenance item",
        "service_or_api": "org_workflows.inbox.collect_inbox_items",
    },
    {
        "order": 6,
        "actor_role": "organisation_admin",
        "module": "F2.14",
        "action": "Reporting dashboard reflects records",
        "service_or_api": "reporting.dashboard.main_dashboard",
    },
]

# UI routes for manual completion (no fake workflows).
ALI_UI_ROUTE_HINTS: list[str] = [
    "/dashboard/case-assignments",
    "/dashboard/support-worker",
    "/dashboard/maintenance",
    "/dashboard/org-workflows/approvals",
    "/dashboard/reports",
]
