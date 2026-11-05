# Tenant Management (F1.6)

## Distinction

| Concept | Meaning |
| --- | --- |
| Tenant person record | Row in `tenants` (housing client profile) |
| Tenant role | `hmore_role.tenant` on `organisation_memberships` |
| Auth0 user | Mapped to `users` (F1.3) |

Creating a tenant person does **not** create an Auth0 account.

## Endpoints

| Method | Path | Permission |
| --- | --- | --- |
| POST | `/api/v1/tenants` | `tenants.manage` |
| GET | `/api/v1/tenants` | `tenants.read` |
| GET | `/api/v1/tenants/{id}` | `tenants.read` |
| PATCH | `/api/v1/tenants/{id}` | `tenants.manage` |
| DELETE | `/api/v1/tenants/{id}` | `tenants.manage` (archives) |

Query params: `page`, `page_size`, `q`, `status`.

## Fields

preferred_name (required), full_name, email, phone, tenancy_reference, consent_notes, consent_given_at, preferences, needs_goals, notes, status, user_id (optional link), timestamps.

## Access

- Organisation Admin: manage within org
- Support Worker: read within org
- Tenant role: read only own linked record (`user_id` match)
- Contractors: no tenant person access
