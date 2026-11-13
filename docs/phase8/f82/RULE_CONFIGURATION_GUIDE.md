# Rule Configuration Guide

Each rule includes: name, description, `trigger_type`, `trigger_config`, category, priority, responsible team, notification method, and enabled flag.

## Supported trigger types

- `repeated_missed_appointments` — `threshold`, `window_days`
- `multiple_unresolved_support_tasks` — `threshold`
- `repeated_reported_incidents` — `threshold`, `window_days`
- `overdue_safeguarding_followups`
- `repeated_welfare_concerns` — `threshold`, `window_days`
- `unresolved_urgent_maintenance`
- `support_plan_review_failures`

Default rules ship **disabled** until an Organisation Admin enables them after local policy review.

Evaluate via `POST /api/v1/safeguarding-alerts/rules/evaluate`.
