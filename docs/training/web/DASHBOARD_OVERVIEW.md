# Web dashboard training overview

Authenticated shell: **Dashboard** (`/dashboard`) with sidebar filtered by permissions (`apps/web/src/lib/navigation.ts`).

## By module

| Module | Path (examples) | Primary roles |
| --- | --- | --- |
| Super Admin | `/dashboard/super-admin`, organisations | Super Admin |
| Organisation Admin | `/dashboard/organisation-admin` | Organisation Admin |
| Landlord enterprise | `/dashboard/landlord` | Landlord, OA |
| Tenants / properties / rooms | `/tenants`, `/properties`, `/rooms` | OA, Landlord |
| Housing | `/dashboard/housing-applications` | OA, SW (read) |
| Support caseload | `/dashboard/caseload`, support-worker home | Support Worker |
| Support plans | `/dashboard/support-plans` | OA, SW |
| Maintenance | `/dashboard/maintenance` | OA, SW, MC, Tenant (limited) |
| Complaints | `/dashboard/complaints` | OA, SW |
| Documents | `/dashboard/documents/*` | OA, SW (tiered) |
| Communications | `/dashboard/communications/*` | OA, SW |
| Reports | `/dashboard/reports/*` | OA, SA (read) |
| Automation | `/dashboard/automation` | OA |
| Integrations | `/dashboard/integrations` | OA, SA |
| AI | ai-activity, ai-costs, feature flags, agents | OA, SA |
| Privacy / backups / performance | Phase 7 operator pages | SA |

## Navigation tips

- Use **Skip to main content** (keyboard) for accessibility.
- Sign out via header **Log out**.
- **Unauthorized** page means missing permission — request access from OA.

## Errors

- 401: session expired — sign in again.
- Empty state: may mean Auth0 not configured in dev — not a training environment issue in production.

## Practice exercise (trainer)

1. Trainer logs in as each role in staging.
2. Trainee lists three visible nav items and one denied URL (expect redirect/unauthorized).
