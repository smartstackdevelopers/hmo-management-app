# Support Caseload, Daily Logs & Handovers (F2.1)

## Scope

Support Worker caseload management, structured daily logs/notes, and staff handovers. No AI, rota, incidents, or Phase 2+ modules beyond F2.1.

## Data model

| Table | Purpose |
| --- | --- |
| `case_assignments` | Org-scoped link of Support Worker ↔ Tenant person |
| `daily_logs` | Structured support activity logs |
| `handovers` | Draft → submitted → acknowledged → completed (or cancelled) |

All tables are organisation-scoped with PostgreSQL RLS (`hmore_org_isolation`).

## Authorisation

- Support Workers access **assigned** tenants only (`assert_assigned_support_caseload`).
- Organisation Admins manage assignments (`tenants.manage`) and have oversight read (`support_notes.read.assigned`).
- Landlords and Tenants do **not** receive support note permissions.
- Workers cannot self-assign tenants.
- Handover recipients must be active Support Workers in the same organisation.
- Note bodies are **not** stored in audit metadata.

## API (prefix `/api/v1`)

- `GET /caseload` — paginated assigned cases (search `q`)
- `GET /caseload/tenants/{id}` — case detail with recent logs/handovers
- `POST /case-assignments`, `POST /case-assignments/{id}/end`
- `POST|GET|PATCH /daily-logs`
- `POST|GET|PATCH /handovers` + `/submit` `/acknowledge` `/complete` `/cancel`

## Web

- `/dashboard/support-worker` — Support Worker home / caseload
- `/dashboard/caseload/[tenantId]` — case view
- `/dashboard/daily-logs/new`, `/dashboard/handovers`, `/dashboard/case-assignments`

UI gates are non-authoritative; API enforces access.
