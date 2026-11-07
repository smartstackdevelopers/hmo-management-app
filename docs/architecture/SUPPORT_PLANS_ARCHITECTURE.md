# F2.10 — Structured Support Plans

## Scope

Tenant-scoped **support plans** with **goals**, **milestones**, **weekly/monthly reviews**, **progress history**, **dashboard aggregates**, and **PDF exports**. This extends F2.9 simple tenant needs/goals; it does not replace the tenant timeline (F2.9).

## Data model

- `tenant_support_plans` — plan header, status workflow, responsible support worker, contributor list (`support_plan_contributors`), versioning via `supersedes_plan_id` / `superseded_by_plan_id`.
- `support_plan_goals` — structured goals; `support_plan_goal_changes` and `support_plan_goal_progress_notes` for history.
- `support_plan_milestones` — per-goal milestones; `support_plan_milestone_changes`.
- `support_plan_reviews` — weekly or monthly reviews (JSON snapshots for goals/milestones optional).
- `support_plan_history_events` — plan-level timeline events.
- `support_plan_progress_exports` — links to `file_metadata` + generated PDF in private storage.

Migration: `apps/api/migrations/versions/20261106_2100_f210_support_plans.py` (RLS via `hmore_org_isolation` on all org-scoped tables).

## Permissions (string values)

| Permission | Purpose |
| --- | --- |
| `support_plans.read` | Read plans/goals/reviews within org scope |
| `support_plans.read.own` | Tenant: read own plans (non-internal fields) |
| `support_plans.manage` | Create/update plans, goals, milestones, draft reviews |
| `support_plans.notes.internal` | View internal notes |
| `support_plans.export` | Generate/download progress PDF |
| `support_plans.review.finalise` | Finalise weekly/monthly reviews |

Role matrix: `apps/api/app/rbac/matrix.py` (Super Admin, Org Admin, Support Worker, Tenant read-own, Landlord read limited; Maintenance & Contractors denied).

## Access rules

- **Support Worker**: active **case assignment** for the tenant (`CaseAssignment`); management uses caseload + `support_plans.manage`.
- **Organisation Admin / Super Admin**: full org scope when impersonating org (Super Admin must send `X-Organisation-Id`).
- **Tenant**: own linked `Tenant.user_id`; `support_plans.read.own`; internal fields and non–`show_to_tenant` progress notes hidden.
- **Landlord**: same property-linked gate as F2.9 timeline (`Complaint` / `MaintenanceRequest` on landlord’s property).

## API (prefix `/api/v1`)

- `GET/POST /tenants/{tenant_id}/support-plans` — list, create.
- `GET/PATCH /tenants/{tenant_id}/support-plans/{plan_id}` — detail, update (editable statuses only).
- Transitions: `activate`, `hold`, `resume`, `review-start`, `complete`, `close`, `revise`.
- Nested: goals, milestones, reviews, exports, `progress-history` (combined chronology).
- `GET /support-plans/dashboard` — aggregates (staff only; support workers scoped to caseload tenants).
- `GET /tenant/support-plans` — tenant self list (resolved tenant from `user_id`).

## Reviews

- Draft/in-progress reviews are mutable; **finalised** reviews are immutable (409 on patch).
- Finalisation requires `support_plans.review.finalise`.
- PDF export text states clearly it is **not** a statutory assessment.

## Testing

- `apps/api/tests/test_f210_support_plans.py` — PostgreSQL: lifecycle, isolation, finalised review protection, PDF smoke.
- `DATABASE_URL` / `TEST_DATABASE_URL` for integration; others are unit/registry tests.

## Frontend

- `/dashboard/support-plans` — progress dashboard (API-driven).
- `/dashboard/support-plans/tenant?tenantId=` — plan listing for a tenant (staff).
