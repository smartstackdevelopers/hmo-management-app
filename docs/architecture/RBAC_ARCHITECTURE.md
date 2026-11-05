# RBAC Architecture (F1.4)

## Purpose

HMore enforces Role-Based Access Control so authenticated users can perform only actions permitted by their assigned roles. Authentication remains Auth0 (F1.3). This document describes the authorization foundation delivered in F1.4.

## Exactly six approved core roles

| Role id | Display name | Scope |
| --- | --- | --- |
| `super_admin` | Super Admin | Platform |
| `organisation_admin` | Organisation Admin | Organisation |
| `landlord` | Landlord | Organisation + owned properties |
| `tenant` | Tenant | Organisation + own records |
| `support_worker` | Support Worker | Organisation + assigned caseload |
| `maintenance_contractor` | Maintenance & Contractors | Organisation + assigned work orders |

No additional core roles are defined. Duties formerly associated with removed titles (Council Officer, Housing Manager, Compliance Officer, Finance Officer, Facilities Manager, Auditor) are absorbed into these six roles where the proposal assigns them — they are not new enums.

Source of truth in code:

- `apps/api/app/db/models/enums.py` (`HMoreRole`)
- `apps/api/app/rbac/roles.py`

## Permission registry

Permissions are a closed `Permission` StrEnum with documented purpose metadata in `PERMISSION_CATALOG`.

- Location: `apps/api/app/rbac/permissions.py`
- Naming: `resource.action` (and `.own` / `.assigned` suffixes where scope is inherent)
- Deny-by-default: unlisted permission → denied
- No wildcard permissions

## Role → permission matrix

Central map: `apps/api/app/rbac/matrix.py` (`ROLE_PERMISSIONS`).

Human-readable matrix: `docs/security/ROLE_PERMISSION_MATRIX.md`.

## Authorization flow

1. Client presents Auth0 access token (F1.3).
2. API resolves the HMore `users` row via `external_subject`.
3. API loads `organisation_memberships` from PostgreSQL (trusted).
4. Optional headers `X-Organisation-Id` / `X-HMore-Role` select among **existing** memberships only.
5. `AuthorizationContext` exposes active role, organisation, and permissions.
6. Route dependencies (`require_perm`) or service helpers enforce checks.
7. Unauthenticated → HTTP 401. Authenticated without permission → HTTP 403.

Client-supplied roles, organisation IDs, or request-body role fields are never treated as authority.

## Components

| Component | Path |
| --- | --- |
| Permissions | `app/rbac/permissions.py` |
| Roles | `app/rbac/roles.py` |
| Matrix | `app/rbac/matrix.py` |
| Context | `app/rbac/context.py` |
| Service / resource checks | `app/rbac/service.py` |
| Assignment rules | `app/rbac/assignment.py` |
| FastAPI deps | `app/rbac/deps.py` |
| HTTP API | `app/api/v1/rbac.py` |
| Session policy | `app/auth/session_policy.py` |
| Web helpers | `apps/web/src/lib/rbac.ts` |

## Role assignment

- Endpoint: `POST /api/v1/rbac/memberships` (requires `role_assignments.manage`)
- Super Admin may assign any approved role (including Super Admin)
- Organisation Admin may assign the five organisation-scoped roles within their organisation only
- Unknown role strings are rejected
- Target user's `authorization_version` increments on change
- No public arbitrary role-change endpoint without authorization

## Database

F1.4 adds `users.authorization_version` (Alembic `20261105_1500_f14`).

Roles and memberships reuse F1.2 tables (`hmore_role` enum, `organisation_memberships`). Permission definitions live in code, not duplicate DB tables, to keep a single registry and avoid drift.

## F1.5 integration boundary

F1.4 provides:

- Permission checks
- Active organisation selection from memberships
- Resource helpers that reject cross-organisation IDs when a helper is used

F1.5 owns:

- Systematic organisation isolation on every data query
- Membership provisioning workflows / onboarding
- Hardening every CRUD path against IDOR across organisations

Calling a resource helper in F1.4 does **not** claim F1.5 is complete.

## Web integration

`apps/web` reuses Auth0 login. `lib/rbac.ts` and `PermissionGate` hide/disable unauthorized UI. Backend enforcement remains mandatory. Role dashboards are F1.9.

## Out of scope

Organisation isolation enforcement (F1.5), CRUD (F1.6), audit writers (F1.7), file storage (F1.8), dashboards (F1.9).
