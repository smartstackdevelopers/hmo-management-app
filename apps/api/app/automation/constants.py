"""Allowed automation triggers/actions — sensitive decisions are forbidden."""

from __future__ import annotations

CATEGORIES = frozenset({"reminder", "escalation", "compliance_sweep"})
FREQUENCIES = frozenset({"hourly", "daily", "weekly", "manual"})
ACTION_TYPES = frozenset(
    {"create_reminder", "escalate_record", "run_compliance_sweep", "create_approval_request"}
)

# Trigger conditions that scan live operational records
TRIGGER_CONDITIONS = frozenset(
    {
        # Reminders
        "appointment_upcoming",
        "appointment_overdue",
        "support_plan_review_upcoming",
        "support_plan_review_overdue",
        "task_pending",
        "task_overdue",
        "inspection_upcoming",
        "inspection_overdue",
        "document_expiry",
        "complaint_action_required",
        "maintenance_scheduled",
        # Escalations
        "complaint_overdue",
        "maintenance_high_priority",
        "followup_missed",
        "task_overdue_escalation",
        "inspection_missed",
        "safeguarding_followup_overdue",
        # Compliance
        "compliance_scheduled_sweep",
    }
)

# Never automate these sensitive outcomes
FORBIDDEN_ACTION_KEYS = frozenset(
    {
        "approve_housing_application",
        "reject_housing_application",
        "change_tenancy_status",
        "reject_tenant",
        "employment_decision",
        "punish_staff",
        "auto_close_complaint",
    }
)

DEFAULT_LEAD_DAYS = 3
