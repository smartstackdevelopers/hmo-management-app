# F3.9 — Compliance Agent

## Overview

Runs a deterministic rules sweep across authorised organisation records, then optionally asks the shared AI service to explain the findings for staff.

This feature does **not** provide legal certification or autonomous compliance decisions. Final decisions and corrective actions stay with authorised human staff.

## Rule sources

Every rule is traceable to an existing HMore operational field or helper:

| Rule ID | Source |
| --- | --- |
| `training.expired` | F2.3 `staff_training_records.expiry_date` |
| `safeguarding.overdue` | F2.3 safeguarding reminder `due_at` / status |
| `incident.follow_up_overdue` | F2.4 incident follow-up `due_at` |
| `support_plan.review_overdue` | F2.10 `planned_review_date` overdue metric |
| `document.expired` | F2.11 managed document expiry tracking |
| `complaint.response_overdue` | F2.7 `is_overdue` helper |

No legislation, statutory deadlines, or regulatory thresholds are invented.

## Workflow

1. Authorised staff (or the daily Celery beat job) starts a sweep.
2. Rules evaluate records in the selected modules.
3. Structured findings are created with deduplication for open issues.
4. AI explains grouped findings when available; budget/cap/unavailable paths keep rule results.
5. Staff confirm, investigate, dismiss, or resolve findings. Source operational records are never mutated by the agent.

## API

| Method | Path |
| --- | --- |
| GET | `/api/v1/compliance-agent/rules` |
| POST | `/api/v1/compliance-agent/sweeps` |
| GET | `/api/v1/compliance-agent/sweeps` |
| GET | `/api/v1/compliance-agent/sweeps/{id}` |
| GET | `/api/v1/compliance-agent/findings` |
| GET | `/api/v1/compliance-agent/findings/{id}` |
| POST | `/api/v1/compliance-agent/findings/{id}/review` |
| POST | `/api/v1/compliance-agent/findings/{id}/resolve` |

## Permissions

| Permission | Roles |
| --- | --- |
| `ai.compliance.run` | Organisation Admin, Super Admin (`compliance.check` also accepted for run/read) |
| `ai.compliance.read` | Organisation Admin, Super Admin |
| `ai.compliance.review` | Organisation Admin, Super Admin |

## Scheduling

Celery beat task `hmore.compliance.dispatch_scheduled_sweeps` runs daily. Organisation-scoped task: `hmore.compliance.dispatch_organisation_sweep`.

## Database

Migration `20261107_2300_f39` adds `compliance_sweeps` and `compliance_findings` with organisation RLS. Open findings are deduplicated by partial unique index on `(organisation_id, dedupe_key)`.

## Known limitations

- Rules cover only verified HMore operational deadlines/expiry fields listed above.
- AI explains findings; it cannot change rule outcomes, invent requirements, resolve findings, or modify source records.
- Corrective actions are recorded as references; staff still use existing module workflows to fix source data.
