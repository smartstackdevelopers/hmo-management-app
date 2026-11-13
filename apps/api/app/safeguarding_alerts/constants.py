"""F8.2 safeguarding alert constants — no clinical risk scoring."""

from __future__ import annotations

DEFAULT_CATEGORIES: tuple[tuple[str, str, str], ...] = (
    ("welfare_concerns", "Welfare concerns", "Recorded welfare-related concerns requiring human review."),
    ("missed_appointments", "Missed appointments", "Missed appointments that may need follow-up."),
    ("repeated_missed_visits", "Repeated missed support visits", "Pattern of missed support visits."),
    ("reported_incidents", "Reported incidents", "Linked or repeated incident reports."),
    ("self_reported_concerns", "Self-reported concerns", "Concerns reported by the tenant themselves."),
    ("housing_instability", "Housing instability", "Housing-related instability indicators."),
    ("maintenance_safety", "Maintenance affecting safety", "Safety-related maintenance issues."),
    ("unresolved_complaints", "Unresolved complaints", "Complaints requiring safeguarding follow-up."),
    ("staff_reported", "Staff-reported safeguarding concerns", "Concerns raised by authorised staff."),
    ("other", "Other authorised concerns", "Other concerns approved by the organisation."),
)

ALERT_STATUSES: frozenset[str] = frozenset(
    {"new", "under_review", "assigned", "action_required", "escalated", "resolved", "closed"}
)

ALERT_PRIORITIES: frozenset[str] = frozenset({"critical", "high", "medium", "low"})

STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "new": frozenset({"under_review", "assigned", "closed"}),
    "under_review": frozenset({"assigned", "action_required", "escalated", "resolved", "closed"}),
    "assigned": frozenset({"under_review", "action_required", "escalated", "resolved", "closed"}),
    "action_required": frozenset({"under_review", "assigned", "escalated", "resolved", "closed"}),
    "escalated": frozenset({"under_review", "assigned", "action_required", "resolved", "closed"}),
    "resolved": frozenset({"closed", "under_review"}),
    "closed": frozenset({"under_review"}),
}

RULE_TRIGGER_TYPES: frozenset[str] = frozenset(
    {
        "repeated_missed_appointments",
        "multiple_unresolved_support_tasks",
        "repeated_reported_incidents",
        "overdue_safeguarding_followups",
        "repeated_welfare_concerns",
        "unresolved_urgent_maintenance",
        "support_plan_review_failures",
    }
)

LANDLORD_VISIBLE_CATEGORY_SLUGS: frozenset[str] = frozenset({"maintenance_safety", "housing_instability"})

PUSH_PREVIEW_SAFE = "Safeguarding alert requires your review. Open the staff app for details."
