# F1.9 Web Dashboard Shell

Foundational authenticated shell for **Super Admin**, **Organisation Admin**, and **Landlord**.

## Routes

| Path | Purpose |
| --- | --- |
| `/dashboard` | Auth required; redirects to role home from API `active_role` |
| `/dashboard/super-admin` | Super Admin home |
| `/dashboard/super-admin/organisations` | Platform organisations entry (empty state) |
| `/dashboard/organisation-admin` | Organisation Admin home |
| `/dashboard/landlord` | Landlord home |
| `/dashboard/files` | Private files shell (needs `files.read`) |
| `/dashboard/audit` | Audit shell (needs `audit_logs.read`) |

Public foundation pages remain under the `(public)` route group (`/`, `/account`, `/health`, `/tenants`, …).

## Authorization

1. Auth0 session via existing `@auth0/nextjs-auth0` middleware and `/auth/*` routes.
2. Role and permissions from `GET /api/v1/rbac/me` using the Auth0 access token.
3. Client storage / query params are **never** trusted for role.
4. Wrong-role direct URLs redirect to `/unauthorized`.
5. Navigation filtering uses the same permission ids as the API matrix — hiding a link is not security.

## Navigation source

`apps/web/src/lib/navigation.ts` → `filterNavItems`.

## Components

`DashboardShell`, `SidebarNav`, `MobileNav`, `UserMenu`, `OrgContextBadge`, `PageHeader`, `EmptyState`, `LoadingState`, `ErrorState`.

## API dependencies

| Need | Status |
| --- | --- |
| Auth0 session | Required for live login |
| `/api/v1/rbac/me` | Required for role routing and nav |
| Tenants/properties/rooms/files/audit list UIs | Not built here — empty states + existing routes/APIs |

## Out of scope

Tenant / Support Worker / Contractor homes, analytics widgets, fake KPIs, F1.10/F1.11 work.
