# F3.13 — Weekly/Monthly Report Drafts + Overdue Reminders

## Overview

1. **Report drafts** — authorised staff generate weekly or monthly drafts. Metrics come from existing F2.14 housing/complaints/caseload summaries. Optional AI narrative organises those verified figures and is labelled **AI-GENERATED DRAFT — REQUIRES HUMAN REVIEW**. Approval never distributes the report.
2. **Overdue reminders** — a Celery scan finds overdue operational tasks, incident follow-ups, and safeguarding reminders using existing due-date rules, then upserts `reminder_records`. Delivery stays on the existing F2.2 reminder dispatch path (`in_app` channel via the foundation notification provider).

## Reporting periods

- Timezone default: `Europe/London` (Organisation has no timezone column yet — documented limitation).
- Weekly: previous complete Monday–Sunday week.
- Monthly: previous complete calendar month.

## Metrics

Deterministic only via `housing_reports`, `complaints_reports`, and `caseload_reports`. AI never invents counts. Unavailable sections for the requester are listed explicitly.

## Human review

Statuses: `draft` → `approved` | `rejected`. Edit body before approval. `distributed` is constrained to `false` in the database.

## Overdue sources

| Resource | Kind | Open statuses |
| --- | --- | --- |
| `operational_task` | `task_overdue` | open, in_progress, blocked |
| `incident_follow_up` | `incident_follow_up_overdue` | open, in_progress, blocked |
| `safeguarding_reminder` | `safeguarding_overdue` | pending, sent, acknowledged, overdue |

Deduplication: unique constraint on `(organisation_id, resource_type, resource_id, reminder_kind, scheduled_for)` where `scheduled_for` is the due timestamp floored to the minute.

## API

| Method | Path |
| --- | --- |
| POST | `/api/v1/report-drafts` |
| GET | `/api/v1/report-drafts` |
| GET | `/api/v1/report-drafts/{id}` |
| PATCH | `/api/v1/report-drafts/{id}` |
| POST | `/api/v1/report-drafts/{id}/review` |

Permissions: `report_drafts.generate|read|review` for Organisation Admin / Super Admin.

## Jobs

- `hmore.overdue_reminders.scan` (hourly)
- `hmore.report_drafts.dispatch_weekly` / `dispatch_monthly`
- Existing `hmore.reminders.dispatch_due` delivers pending rows

## Known limitations

- No organisation timezone field — Europe/London default.
- No email/SMS channel assumed; overdue scan schedules `in_app` only.
- Complaints overdue escalation remains the separate F2.7 job; not reimplemented here.
- AI narrative uses a constrained metrics-echo workflow unless a provider is configured behind the shared AI service.
