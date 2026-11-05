# Organisation Membership (F1.5)

## Model

Table: `organisation_memberships` (F1.2).

| Field | Rule |
| --- | --- |
| `user_id` | FK to `users` |
| `organisation_id` | FK to `organisations`; NULL only for `super_admin` |
| `role` | One of six `hmore_role` values |
| `status` | `active`, `invited`, `suspended` |

Unique: `(user_id, organisation_id)` for org-scoped rows; one Super Admin membership per user (partial unique index).

## Access rules

- Only **active** memberships grant organisation access.
- Suspended/invited memberships are denied by authorization context selection.
- Users cannot assign themselves to arbitrary organisations.
- Users cannot activate their own suspended membership (unless Super Admin platform policy).
- Organisation Admin may manage memberships only inside their organisation for assignable roles.
- Super Admin may create organisations (`POST /api/v1/organisations`) via platform context.

## APIs

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/organisations/me/context` | Current trusted org context |
| POST | `/api/v1/organisations` | Create organisation (Super Admin) |
| GET | `/api/v1/organisations/{id}/memberships` | List memberships (authorized) |
| PATCH | `/api/v1/organisations/memberships/{id}/status` | Activate/suspend |
| POST | `/api/v1/rbac/memberships` | Assign/update role (F1.4) |

## Web

`apps/web/src/lib/organisation.ts` helps select active memberships and build headers. Backend validation is mandatory.
