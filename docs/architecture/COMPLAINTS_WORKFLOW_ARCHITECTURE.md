# Complaints Workflow (F2.7)

## Scope

Organisation-scoped complaints with priorities, operational deadlines, investigation notes, escalations, and history. Reuses F1.8 private files and F2.2 Celery/Redis.

**Not in scope:** statutory complaint categories or legal response periods, F2.8+ features, AI classification, new notification platforms.

## Lifecycle

`submitted → acknowledged → under_review → investigation | awaiting_information | escalated → resolved → closed`

Also: withdraw from early states; `closed|resolved → reopened`; reopen returns to active review states.

Invalid transitions are rejected by the backend. Closing, withdrawing, resolving, and reopening require an explanation.

## Priorities

`low | normal | high | urgent` — operational labels only. Priority changes are audited and do not assert legal outcomes.

## Deadlines

Organisation `complaint_deadline_rules` define acknowledge/response hours per priority. Defaults are **internal operational targets**, not statutory deadlines. Deadline edits require a reason and are historied.

## Escalations

Manual escalation (OA) and automatic overdue escalation (Celery beat every 15 minutes). Duplicate prevention via `idempotency_key` unique per complaint.

## Notes visibility

- `internal` — never returned to tenants or roles without `complaints.notes.internal`
- `tenant_visible` — available to authorised complainants

## Permissions

| Role | Access |
| --- | --- |
| Organisation Admin | Full manage, assign, priority, deadlines, escalate, close, internal notes |
| Support Worker | Create/read assigned caseload; add notes |
| Tenant | Create/read own; tenant-visible notes/history only |
| Landlord | Read complaints linked to permitted properties |
| Maintenance | Denied by default |

## Background jobs

- `hmore.complaints.dispatch_overdue` — platform scan
- `hmore.complaints.dispatch_organisation_overdue` — org-scoped payload via `JobOrganisationContext`

## APIs

`/api/v1/complaints` (+ dashboard, categories, seed-defaults, assign, priority, transition, notes, deadlines, escalate, escalations, history, files)

## Migration

`20261106_1800_f27`
