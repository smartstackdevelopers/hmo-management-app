# Staff mobile app — user manual

**Who:** Support Worker (primary), plus staff routes for incidents, occupancy, approvals.

## Installation & login

Same HMore binary as tenant — role from Auth0 determines shell after login.

## Staff areas

| Feature | Where | Notes |
| --- | --- | --- |
| Caseload | `(tabs)/caseload`, `staff/case/[tenantId]` | Assigned tenants only |
| Shifts | `(tabs)/shifts` | Rota integration |
| Daily notes | `(tabs)/notes` | Voice dictation optional |
| Visits / tasks | `staff/visits`, `staff/tasks` | |
| Work orders | `(tabs)/work-orders` | Contractors overlap |
| Incidents | `staff/incidents` | |
| Approvals | `staff/approvals` | Supervisor flows |
| Occupancy | `staff/occupancy` | RBAC + DPIA gate |
| Offline drafts | `offline-drafts` | Encrypted queue |
| Security | `security` | Biometric, device sessions |

## Voice dictation

1. Open note editor → dictate.
2. Review transcript; optional AI rewrite — still staff responsibility.
3. Save — syncs when online unless offline draft.

## Push notifications

Registered after session; token stored server-side per device.

## Biometric unlock

Unlocks existing session only — does not replace Auth0 login.

## Remote sign-out / lost device

**Security** → report lost device; OA/Admin can revoke session server-side.

## Sync status

Failed sync shows error — do not discard draft until IT reviews (`offlineSync` tests document behaviour).

## Practice exercise

1. Create offline draft (airplane mode).
2. Reconnect → confirm sync or readable error.
