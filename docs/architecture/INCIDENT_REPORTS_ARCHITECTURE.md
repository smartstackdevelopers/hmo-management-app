# Incident Reports, Follow-ups & Workload (F2.4)

## Scope

Operational incident reporting, follow-up action tracking, and staff workload summaries built from live F2.1–F2.3 data. Not a full safeguarding case system and not F2.14 analytics.

## Data model

| Table | Purpose |
| --- | --- |
| `incidents` | Org-scoped incident reports with reference numbers |
| `incident_status_history` | Status transition history |
| `incident_follow_ups` | Action tracking linked to incidents |

Evidence uses existing F1.8 `file_metadata` (`resource_type` / `resource_id`) — no second storage system.

## Reminders

Reuses F2.2 `reminder_records` for follow-up due/overdue and assignment notices. Delivery remains `log_stub` until F2.12.

Config: `REMINDER_INCIDENT_FOLLOW_UP_LEAD_MINUTES` (default 1440).

## Workload

Aggregates assigned tenants, open/overdue tasks, upcoming visits, pending handovers, and open/overdue incident follow-ups. Org Admin sees organisation scope; Support Workers see own workload only.

## APIs

`/api/v1/incidents`, `/api/v1/incident-follow-ups`, `/api/v1/workload`
