# F8.2 Safeguarding Alert System Architecture

## Purpose

Optional add-on that helps authorised staff **identify, record, review, and respond** to safeguarding concerns. It complements (does not replace) F2.3 safeguarding reminders, F2.4 incidents, F2.7 complaints, F2.1 daily logs, and F2.10 support plans.

## Components

| Layer | Location |
|-------|----------|
| API | `apps/api/app/api/v1/safeguarding_alerts.py` |
| Domain | `apps/api/app/safeguarding_alerts/` |
| Models | `apps/api/app/db/models/safeguarding_alerts.py` |
| Migration | `20261114_5000_f82` |
| Web dashboard | `apps/web/src/app/dashboard/safeguarding-alerts/` |
| Staff mobile | `room-ready/app/(app)/staff/safeguarding-alerts.tsx` |

## Human-in-the-loop

- Rule engine creates **suggestions** (`source_type=rule`) with `requires_human_review=true`.
- AI assist produces **drafts only**; approval required before optional alert creation.
- No automated risk scores, diagnoses, or case closure without authorised human action.

## Platform gate

`SAFEGUARDING_ALERTS_GLOBAL_ENABLED=false` by default. Organisation settings `enabled` must also be true.

## Notifications

Uses F2.12 communication outbox via `ReminderMessage`. Push bodies use generic preview text only.
