# Maintenance & repairs (F2.8)

## Scope

Organisation-scoped maintenance requests with configurable categories, priority levels (including audited emergency), full status workflow, optional approval gate, private photo evidence (F1.8), visit scheduling (with optional link to F2.2 `tenant_visits`), history timeline, and organisation-managed gas/fire **emergency instruction** content.

**Not in scope:** contractor marketplace, billing, procurement, multi-level financial approval, AI repair triage, new notification platforms, F2.9+ features.

## Categories & priority

- Categories are per-organisation rows in `maintenance_categories`, seeded by `POST /api/v1/maintenance/seed-defaults` or created via `POST /api/v1/maintenance/categories`.
- Operational labels only — not statutory classifications.
- Categories may set `triggers_emergency_panel` and `emergency_kind` (`gas` | `fire`) to surface approved emergency guidance in the UI when combined with priority/category context.
- Priority: `low | normal | high | urgent | emergency`. Changes require `maintenance.priority.manage` (Organisation Admin) and are stored in `maintenance_priority_changes` with reason.
- Tenants cannot set `emergency` on create; staff must review (prevents unverified auto-emergency from free text alone).

## Status lifecycle

Valid transitions are enforced in `app/maintenance/service.py` (`MAINT_TRANSITIONS`). Completion uses `POST .../complete` (work notes required), not a generic transition to `completed`.

States include: submitted, acknowledged, under_review, awaiting_approval, approved, rejected, assigned, scheduled, in_progress, awaiting_parts, on_hold, completed, closed, reopened, cancelled.

Reasons are required for: rejected, cancelled, reopened, on_hold (aligned with `REASON_STATUSES`).

Closing and reopening require `maintenance.close` (Organisation Admin / Super Admin path in transition handler).

If `requires_approval` is true, progression to assigned/scheduled/in_progress/awaiting_parts/completed is blocked until `approval_status == approved`.

## Visits

`maintenance_visits` rows track schedule, reschedule, cancel, complete, and missed outcomes. Optional `linked_tenant_visit_id` aligns with F2.2 casework visits.

Assignee/time conflict checks apply when both assignee and slot are set.

## Photos & files

Upload: `POST /api/v1/maintenance/{id}/files/upload` (multipart). Association: `POST .../files` with existing `file_id`.

Authorised download: `GET /api/v1/maintenance/{id}/files/{file_id}/content` — enforces `maintenance.photo.read` **and** request-level visibility (not `files.read` alone).

## Emergency gas / fire content

Stored per org in `maintenance_emergency_content`. Seeded placeholders require `requires_formal_approval` and `approved_for_use=false` until the organisation replaces them with approved operational text.

## APIs

`/api/v1/maintenance` — dashboard, categories, seed-defaults, emergency `{gas|fire}`, CRUD-style workflow (create, list, get, patch), assign, priority, transition, approval, schedule, visit lifecycle, notes, history, files upload/associate/download, complete.

## RBAC (summary)

| Role | Access |
| --- | --- |
| Organisation Admin | Full maintenance.manage capabilities |
| Support Worker | Create/read assigned scope; schedule; notes |
| Tenant | Create/read own; tenant-visible notes |
| Landlord | Read property-scoped requests; view photos |
| Maintenance contractor | Assigned or visit-linked requests only; schedule own visits; complete with scope checks |
| Super Admin | Platform oversight where token selects org — matrix does not grant maintenance permissions; service bypasses explicit checks where noted |

## Migration

`20261106_1900_f28_maintenance` (maintenance tables + RLS policies).
