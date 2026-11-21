# PROMPT 6 — Remaining issues

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Branch | `develop` @ `60b2f02` |

## Environment blockers

| Issue | Severity | Action |
| --- | --- | --- |
| Docker Desktop stopped | High | Start Postgres; set `TEST_DATABASE_URL` to `hmore_test`; re-run Prompt 6 pytest subset |
| Auth0 browser E2E not run | Medium | `start-meeting-demo.ps1` + six-role walkthrough for M10.1–M10.2 |
| Uncommitted Prompt 3 work in tree | Info | **Not** part of Prompt 6 commit — separate sprint |

## Module gaps

| Module | Gap | Target status |
| --- | --- | --- |
| M10.1 | Super Admin org UI unverified in browser | LOCAL PASS |
| M10.2 | Approvals inbox empty-state only without seeded data | LOCAL PASS with demo data |
| M10.3–M10.4 | Postgres workflow/sharing tests skipped | Re-run when DB up |
| M14.1 | Survey web page is shell; forms deferred | PARTIAL acceptable until UI build |
| F6.1 | Landlord enterprise DB flow skipped | Re-run `test_landlord_enterprise_flow_and_isolation` |
| Automation | No live Celery/Redis smoke | Optional P5 |

## Explicitly deferred / optional

| Item | Status |
| --- | --- |
| M14.3 camera ingest | **DEFER** |
| M10.5 Council Portal | **OPTIONAL** — implemented; not gate |
| Finance payment gateway | **Not mandatory** |
| Contractor marketplace | **Not mandatory** |
| Integration hub | **Not mandatory** (beat hook exists) |

## Local 100% gate (`HMORE_FEATURE_LOCAL_100_PLAN.md`)

| Gate | Prompt 6 impact |
| --- | --- |
| ≥ 50/56 LOCAL PASS | **NO** — enterprise modules **PARTIAL**; browser + DB not proven |
| Mandatory M10.1–M10.2 PASS | **Not met** for strict LOCAL PASS |
| pytest green | **PARTIAL** — 55/70 subset pass; 15 skipped; full suite not re-run |

## Recommended next steps (Prompt 7 not executed here)

1. Start Docker + `alembic upgrade head` on `hmore_test`.
2. Re-run Prompt 6 pytest subset → expect 70 passed if DB healthy.
3. Demo org_admin: approvals, workflows, sharing; super_admin: organisations.
4. Landlord + room-occupancy dashboard smoke in browser.