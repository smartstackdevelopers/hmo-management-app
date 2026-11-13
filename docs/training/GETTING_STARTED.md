# Getting started with HMore

## What HMore is

HMore is a shared platform for housing, support, maintenance, documents, and (where enabled) community and employment tools. **Web:** Next.js dashboard. **Mobile:** Expo app (`room-ready`) for tenants and staff.

## The six roles

| Role | Typical access |
| --- | --- |
| Super Admin | All organisations, platform monitoring, audit, backups (where permitted) |
| Organisation Admin | One organisation — users, housing, compliance, reports |
| Landlord | Portfolio, rent, inspections, maintenance oversight |
| Tenant | Own housing, repairs, support, mobile self-service |
| Support Worker | Caseload, notes, visits, tasks, limited occupancy |
| Maintenance & Contractor | Assigned work orders and repair updates |

Authoritative permissions: `docs/security/ROLE_PERMISSION_MATRIX.md`.

## Sign in

1. Open the URL your organisation provides (web: `/auth/login`, mobile: HMore app).
2. Use **Auth0** — email/password and **MFA** when your organisation requires it.
3. After login, the app shows only menus your role and permissions allow.

**Common mistake:** Assuming a hidden menu means you have access — always confirm with an Organisation Admin if you need a permission.

## Web navigation

After login, use the **left sidebar** (desktop) or **Menu** (mobile width). Items come from `DASHBOARD_NAV` permissions — see your Organisation Admin if a module is missing.

Role homes:

- Super Admin → `/dashboard/super-admin`
- Organisation Admin → `/dashboard/organisation-admin`
- Landlord → `/dashboard/landlord`
- Support Worker → `/dashboard/support-worker`
- Tenant → `/account` (web); primary UX is **mobile**

## Mobile

Install from your organisation’s approved store build (when published). Sign in with the same Auth0 tenant. Enable notifications only if your role uses reminders.

## Getting help

1. This knowledge base under `docs/training/`.
2. Organisation support contact — **PENDING** (set by project owner).
3. Report incidents per [security/SECURITY_PRIVACY_AWARENESS.md](./security/SECURITY_PRIVACY_AWARENESS.md).

## Security basics

- Never share your password or MFA device.
- Only open tenant records you are assigned or permitted to view.
- Log out on shared devices; use **Report lost device** on mobile when needed.
