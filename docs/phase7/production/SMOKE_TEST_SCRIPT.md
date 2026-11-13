# Production smoke test script (controlled)

**Execution status (2026-11-12):** **NOT RUN** — no production environment.

Use **approved test organisation** and **fictional test accounts** only. Never use real tenant PII.

## Preconditions

- [ ] Deployment approval gate **PASS**
- [ ] Production base URL: `CONFIG_PLACEHOLDER`
- [ ] Test accounts created in Auth0 production tenant

## Tests

| # | Test | Steps | Pass criteria |
| --- | --- | --- | --- |
| 1 | Website availability | `GET /` and `/health` via HTTPS | 200, no cert errors |
| 2 | Login + MFA | Staff admin test user | Session established |
| 3 | Six-role permissions | One denied route per non-admin role | 403 as expected |
| 4 | Organisation isolation | User A cannot read Org B tenant | 404/403 |
| 5 | Tenant record CRUD | Create/read test tenant | Audit row |
| 6 | Housing application | Submit + list in queue | 201/200 |
| 7 | Support plan | Create plan with goal | Persisted |
| 8 | Maintenance request | Tenant report repair | Ticket created |
| 9 | Document upload | Upload small test PDF | Private storage key |
| 10 | Report export | CSV export authorised role | Stream 200 |
| 11 | Notification | Trigger test push/email | Provider receipt |
| 12 | AI service | Tenant assistant cached Q | 200, no secret leak |
| 13 | Background job | Trigger backup or schedule tick | `backup_runs` / run row |
| 14 | Mobile API | Prod build login | Token + API 200 |
| 15 | DB health | API health + no pool errors | `status: ok` |
| 16 | Backup dashboard | Super Admin view | Recent run |

## Record results

Log in deployment report section 12. Attach timestamps and request IDs — **no** production data in Git.
