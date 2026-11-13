"""F8.11 workflow triggers, templates, and step types."""

from __future__ import annotations

STEP_TYPES: tuple[str, ...] = (
    "start",
    "end",
    "approval",
    "condition",
    "action",
    "delay",
    "notification",
    "api_action",
)

WORKFLOW_TRIGGERS: tuple[tuple[str, str], ...] = (
    ("tenant_registered", "New tenant registration"),
    ("property_registered", "New property registration"),
    ("rent_payment_received", "Rent payment received"),
    ("rent_payment_overdue", "Rent payment overdue"),
    ("maintenance_request_created", "Maintenance request created"),
    ("maintenance_request_updated", "Maintenance request updated"),
    ("contractor_assigned", "Contractor assigned"),
    ("tenancy_agreement_created", "Tenancy agreement created"),
    ("tenancy_expiry_approaching", "Tenancy agreement approaching expiry"),
    ("lms_course_completed", "Training course completed"),
    ("certification_expiring", "Certification expired or approaching expiry"),
    ("support_case_created", "Support case created"),
    ("support_case_escalated", "Support case escalated"),
    ("benefits_application_submitted", "Benefits application submitted"),
    ("document_uploaded", "Document uploaded"),
    ("digital_signature_completed", "Digital signature completed"),
    ("scheduled_datetime", "Scheduled date and time"),
    ("external_api_event", "External API event"),
)

WORKFLOW_TEMPLATES: tuple[tuple[str, str, list], ...] = (
    (
        "tenant_onboarding",
        "Tenant onboarding",
        [
            {"key": "start", "type": "start"},
            {"key": "notify_staff", "type": "notification", "channel": "in_app"},
            {"key": "approval", "type": "approval", "required_role": "organisation_admin"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "rent_payment_reminder",
        "Rent payment reminders",
        [
            {"key": "start", "type": "start"},
            {"key": "check_overdue", "type": "condition", "operator": "and"},
            {"key": "remind", "type": "notification", "channel": "email"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "rent_overdue_escalation",
        "Rent overdue escalation",
        [
            {"key": "start", "type": "start"},
            {"key": "escalate", "type": "action", "action": "escalate_record"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "maintenance_handling",
        "Maintenance request handling",
        [
            {"key": "start", "type": "start"},
            {"key": "assign_review", "type": "approval", "required_role": "support_worker"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "contractor_assignment",
        "Contractor assignment",
        [
            {"key": "start", "type": "start"},
            {"key": "notify_contractor", "type": "notification", "channel": "in_app"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "tenancy_renewal",
        "Tenancy renewal reminders",
        [
            {"key": "start", "type": "start"},
            {"key": "delay", "type": "delay", "days": 30},
            {"key": "notify", "type": "notification", "channel": "email"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "lms_completion",
        "Training completion notifications",
        [
            {"key": "start", "type": "start"},
            {"key": "notify", "type": "notification", "channel": "in_app"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "certification_expiry",
        "Certification expiry reminders",
        [
            {"key": "start", "type": "start"},
            {"key": "remind", "type": "notification", "channel": "email"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "support_escalation",
        "Support case escalation",
        [
            {"key": "start", "type": "start"},
            {"key": "escalate", "type": "action", "action": "escalate_record"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "benefits_update",
        "Benefits application updates",
        [
            {"key": "start", "type": "start"},
            {"key": "notify", "type": "notification", "channel": "in_app"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "document_approval",
        "Document approval",
        [
            {"key": "start", "type": "start"},
            {"key": "approval", "type": "approval", "required_role": "organisation_admin"},
            {"key": "end", "type": "end"},
        ],
    ),
    (
        "esign_complete",
        "Digital signature completion",
        [
            {"key": "start", "type": "start"},
            {"key": "notify", "type": "notification", "channel": "in_app"},
            {"key": "end", "type": "end"},
        ],
    ),
)

ADDON_DISCLAIMER = (
    "AI suggestions require human approval before publish. Live triggers delegate actions to F6.3 automation where configured."
)

AI_NOTICE = "[AI-generated suggestion]"
