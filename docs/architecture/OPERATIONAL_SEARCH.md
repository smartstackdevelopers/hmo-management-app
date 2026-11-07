# F3.12 — Natural-language search over operational data

## Overview

Authorised staff ask a question. The system turns it into an allowlisted search specification and runs that specification through existing SQLAlchemy models. The AI service, when configured, only returns the specification. It never receives operational records and never executes SQL.

Raw AI-generated SQL is never executed.

## Workflow

1. Authenticate and resolve organisation plus role.
2. Interpret the question (shared AI workflow `operational_search`, or a deterministic parser when AI is unconfigured or unavailable).
3. Validate the specification: known entity, known preset, safe limit, no SQL, no organisation id from the model.
4. Apply role permissions and, where the role is assignment-scoped, filter to assigned records or the worker’s active caseload.
5. Return display fields and a link to the existing record screen.

Organisation id always comes from the server session, not the question or the model output.

## Supported entities

| Entity | Presets | Notes |
| --- | --- | --- |
| `maintenance_request` | open, overdue_open (scheduled visit in the past), awaiting_approval | Contractors see assigned requests only |
| `complaint` | open, overdue_open (`response_due_at`) | Assigned-only roles see their assignments |
| `housing_application` | open, awaiting_approval (`submitted`, `under_review`, `information_required`) | Support workers see assigned tenants only |
| `incident_follow_up` | outstanding_follow_up, overdue_open | Assigned-only unless incidents are managed org-wide |
| `support_plan` | open, overdue_open (`planned_review_date`) | Caseload filter for assigned support plans |
| `operational_task` | open, overdue_open, assigned_to_me | Non-admin users see their own tasks |
| `managed_document` | open, expiring_soon (expiry within 30 days) | Metadata only |
| `staff_training` | open, expiring_soon | Own records unless training is managed org-wide |

Unsupported examples stay unsupported: notes, handovers, safeguarding case content, approvals inbox, and any field not listed above.

## Security

- Tenants cannot call this search.
- Cross-organisation rows are excluded by organisation id and RLS.
- Specifications containing `sql`, `organisation_id`, unknown entities, or limits above 50 are rejected.
- Interpretation cache keys include the organisation id and store the specification only, not result rows.
- Usage caps: a 402 from the AI service is returned as “AI usage limit reached” and is not bypassed.

## API

`POST /api/v1/operational-search` with `{ "question": "..." }`.

Permission: `operational_search.run` (Organisation Admin, Super Admin, Landlord, Support Worker, Maintenance & Contractors). Entity permissions still apply.

## Known limitations

- Interpretation is a constrained parser (and the same parser in the AI workflow). It does not invent filters beyond the presets above.
- Maintenance “overdue” uses `scheduled_visit_at`, because maintenance requests have no separate due-date column.
- No new database tables or indexes. Queries use existing organisation/status/assignee indexes.
