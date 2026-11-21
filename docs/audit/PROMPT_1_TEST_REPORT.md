# PROMPT 1 — Test Report

**Executed:** 14 November 2026 (local machine)

## Pytest (`apps/api`)

| Run | Command | Result |
|-----|---------|--------|
| Full suite | `python -m pytest -q` | **530 passed**, 0 failed, 6 warnings (~153s) |
| Targeted | `test_upgrade_downgrade_roundtrip`, `test_super_admin_organisations_api.py`, `test_unknown_permission_rejected` | **All passed** |

**Database:** `TEST_DATABASE_URL` / `hmore_test` on localhost PostgreSQL.

**Notable tests (new/回归):**

- `tests/test_super_admin_organisations_api.py::test_platform_organisations_list_requires_super_admin`
- `tests/test_super_admin_organisations_api.py::test_create_organisation_super_admin`
- `tests/test_db_schema.py::test_upgrade_downgrade_roundtrip`

## Web (`apps/web`)

| Check | Command | Result |
|-------|---------|--------|
| TypeScript | `npm run typecheck` | **PASS** |
| ESLint | `npm run lint` | **PASS** (pre-existing hook dependency warnings only) |
| Production build | `npm run build` | **PASS** |

**Web unit tests:** none in repo for this page.

## Mobile (`room-ready`)

| Check | Command | Result |
|-------|---------|--------|
| Jest | `npm test -- --testPathPattern=tenantMobile` | **14 passed** (includes new legacy URL tests) |

## Not executed

- Playwright E2E (`npm run test:e2e`)
- Manual Super Admin login in browser
- Expo app on device/emulator against live Auth0

## Pass / fail counts (this sprint verification)

| Suite | Passed | Failed |
|-------|--------|--------|
| API pytest | 530 | 0 |
| Web typecheck/build | 3 checks | 0 |
| Mobile Jest (tenantMobile) | 14 | 0 |

## Pytest green?

**YES** — full local suite passed after fixes.