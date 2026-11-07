"""Allowlisted operational search entities. No raw SQL, no arbitrary columns."""

from __future__ import annotations

from app.rbac.permissions import Permission

MAX_LIMIT = 50
DEFAULT_LIMIT = 25

ENTITIES = (
    "maintenance_request",
    "complaint",
    "housing_application",
    "incident_follow_up",
    "support_plan",
    "operational_task",
    "managed_document",
    "staff_training",
)

PRESETS = (
    "open",
    "overdue_open",
    "awaiting_approval",
    "outstanding_follow_up",
    "expiring_soon",
    "assigned_to_me",
)

# Entity -> permissions that may search it. Org-wide vs assigned is decided in the executor.
ENTITY_PERMISSIONS: dict[str, tuple[Permission, ...]] = {
    "maintenance_request": (
        Permission.MAINTENANCE_MANAGE,
        Permission.MAINTENANCE_READ_ASSIGNED,
        Permission.MAINTENANCE_READ_PROPERTY,
    ),
    "complaint": (
        Permission.COMPLAINTS_MANAGE,
        Permission.COMPLAINTS_READ_ASSIGNED,
        Permission.COMPLAINTS_READ_PROPERTY,
    ),
    "housing_application": (
        Permission.APPLICATIONS_MANAGE,
        Permission.APPLICATIONS_REVIEW,
        Permission.APPLICATIONS_READ_ASSIGNED,
    ),
    "incident_follow_up": (
        Permission.INCIDENTS_MANAGE,
        Permission.INCIDENTS_READ_ASSIGNED,
    ),
    "support_plan": (
        Permission.SUPPORT_PLAN_MANAGE,
        Permission.SUPPORT_PLANS_MANAGE_ASSIGNED,
    ),
    "operational_task": (Permission.TASKS_MANAGE_ASSIGNED,),
    "managed_document": (Permission.DOCUMENTS_READ_META,),
    "staff_training": (
        Permission.TRAINING_RECORDS_MANAGE,
        Permission.TRAINING_RECORDS_READ_OWN,
    ),
}

ORG_WIDE_PERMISSIONS: dict[str, tuple[Permission, ...]] = {
    "maintenance_request": (Permission.MAINTENANCE_MANAGE, Permission.MAINTENANCE_READ_PROPERTY),
    "complaint": (Permission.COMPLAINTS_MANAGE, Permission.COMPLAINTS_READ_PROPERTY),
    "housing_application": (Permission.APPLICATIONS_MANAGE, Permission.APPLICATIONS_REVIEW),
    "incident_follow_up": (Permission.INCIDENTS_MANAGE,),
    "support_plan": (Permission.SUPPORT_PLAN_MANAGE,),
    "operational_task": (),
    "managed_document": (Permission.DOCUMENTS_READ_META,),
    "staff_training": (Permission.TRAINING_RECORDS_MANAGE,),
}

OPEN_MAINTENANCE = (
    "submitted",
    "acknowledged",
    "under_review",
    "awaiting_approval",
    "approved",
    "assigned",
    "scheduled",
    "in_progress",
    "awaiting_parts",
    "on_hold",
    "reopened",
)
OPEN_COMPLAINTS = (
    "submitted",
    "acknowledged",
    "under_review",
    "investigation",
    "awaiting_information",
    "escalated",
    "reopened",
)
PENDING_APPLICATIONS = ("submitted", "under_review", "information_required")
OPEN_FOLLOW_UPS = ("open", "in_progress", "blocked")
ACTIVE_PLANS = ("active", "under_review")
OPEN_TASKS = ("open", "in_progress", "blocked")

RECORD_LINKS = {
    "maintenance_request": "/dashboard/maintenance/{id}",
    "complaint": "/dashboard/complaints/{id}",
    "housing_application": "/dashboard/housing-applications/{id}",
    "incident_follow_up": "/dashboard/incidents/{incident_id}",
    "support_plan": "/dashboard/support-plans",
    "operational_task": "/dashboard/tasks",
    "managed_document": "/dashboard/documents/{id}",
    "staff_training": "/dashboard/training",
}
