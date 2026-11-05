# Organisation Isolation Architecture (F1.5)

## Purpose

HMore is multi-organisation. Each organisation has a protected data boundary. Users from organisation A must not read, update, list, search, or delete organisation B data unless an **explicit** platform-level Super Admin operation is used.

Authentication remains F1.3 (Auth0). Permissions remain F1.4 (RBAC). F1.5 adds organisation membership enforcement, trusted context resolution, query scoping, and defence-in-depth RLS.

## Ownership model

| Entity | Organisation ownership |
| --- | --- |
| `organisations` | Root tenant |
| `organisation_memberships` | Links user ↔ org (nullable org only for Super Admin) |
| `tenants`, `properties`, `rooms` | Required `organisation_id` |
| `file_metadata`, `emergency_access_grants` | Required `organisation_id` |
| `audit_events` | Nullable `organisation_id` (platform actions) |
| `users` | Global identity; access via memberships |

## Context resolution

1. Validate Auth0 access token (F1.3).
2. Resolve HMore `users` row.
3. Load memberships from PostgreSQL.
4. Optional `X-Organisation-Id` / `X-HMore-Role` select among **assigned active** memberships only.
5. `get_organisation_context` requires a non-null organisation id.
6. Super Admin must send `X-Organisation-Id` for ordinary org-scoped endpoints (no accidental global tenant access).
7. `get_platform_context` is the only explicit Super Admin platform path (RLS bypass).

Client-supplied `user_id`, `organisation_id`, `role`, or permissions are never trusted as authority.

## Application isolation

Package: `apps/api/app/tenancy/`

- `isolation.py` — scoped list/get/update/delete helpers
- `membership_service.py` — membership status and org creation rules
- `deps.py` — FastAPI organisation / platform dependencies
- `jobs.py` — background job org payload contract
- `session_rls.py` — `SET LOCAL` helpers

Isolation probes (not F1.6 product CRUD): `/api/v1/isolation/properties`

Probes require both trusted organisation context **and** the matching F1.4 permission
(`properties.read` / `properties.manage`). Membership alone is not enough.

## Database RLS

Enabled with `FORCE ROW LEVEL SECURITY` on: `tenants`, `properties`, `rooms`, `file_metadata`, `emergency_access_grants`.

Policy allows a row when:

- `app.rls_bypass = on` (explicit platform transaction), or
- `organisation_id` matches `app.organisation_id` (SET LOCAL)

`SET LOCAL` is transaction-scoped and does not leak across pool checkouts after commit/rollback.

Organisation-scoped requests run `SET LOCAL ROLE hmore_app` because PostgreSQL **superusers bypass RLS** even with FORCE. Platform bypass resets the role.

**RLS is defence in depth.** Application filters remain mandatory.

## Background jobs

`JobOrganisationContext` requires `organisation_id` in the payload. `validate_job_organisation_context` verifies the organisation exists and, by default, requires `actor_user_id` with an active membership (or Super Admin). Full Celery workflows are later-phase work.

## Out of scope

F1.6 CRUD product APIs, F1.7 audit writers, F1.9 dashboards.
