# PROMPT 12 — Remaining Issues

| ID | Issue | Severity | Status |
| --- | --- | --- | --- |
| P12-1 | Postgres/Docker unavailable — Alembic `20261124_6000_p12` not applied | High | **BLOCKED** |
| P12-2 | Full registration→approval→login E2E not executed against live API | High | **BLOCKED** |
| P12-3 | `@auth0/nextjs-auth0` still listed in web package.json | Medium | **PARTIAL** |
| P12-4 | Dedicated CSRF token for non-server-action cookie POSTs | Medium | **PARTIAL** |
| P12-5 | Native MFA replacement for Auth0 `amr` staff policy | Medium | **UNVERIFIED** / deferred |
| P12-6 | Mobile Jest + Playwright suites not re-run this sprint | Medium | **UNVERIFIED** |
| P12-7 | Email/SMS approval delivery | Low | Documented unavailable without provider |
| P12-8 | Historical Auth0 docs still present | Low | Migration notes OK |

## Next actions (when Postgres is up)

1. `alembic upgrade head`  
2. `POST /api/v1/auth/bootstrap-super-admin`  
3. Create Org Admin → register tenant → approve → login  
4. Remove `@auth0/nextjs-auth0` after web smoke  
5. Expand pytest integration module for Prompt 12  

## Sprint gate

**Not claiming full FINAL ACCEPTANCE** until P12-1 and P12-2 clear.

Overall Prompt 12 delivery: **PARTIAL** — architecture and code landed; live verification blocked.
