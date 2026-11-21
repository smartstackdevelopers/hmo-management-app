# PROMPT 6 — Test execution report

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Branch | `develop` @ `60b2f02` |
| Host | Windows — **Docker Desktop not running**; `DATABASE_URL` not exported to shell (pytest skips `@pytest.mark.postgres`) |

## Prompt 6 subset (single combined run)

```powershell
cd "D:\hmore app\apps\api"
.\..\..\..\.venv\Scripts\pytest.exe -q `
  tests/test_f812_platform_governance.py `
  tests/test_f213_org_workflows.py `
  tests/test_super_admin_organisations_api.py `
  tests/test_f61_landlord_enterprise.py `
  tests/test_f811_advanced_automation.py `
  tests/test_f65_room_occupancy.py `
  tests/test_f110_occupancy_survey.py `
  tests/test_organisation_isolation.py `
  tests/test_rbac_registry.py `
  tests/test_f68_phase6_celery_beat.py `
  tests/test_f62_reports_analytics.py
```

| Metric | Count |
| --- | ---: |
| **Collected** | 70 |
| **Passed** | **55** |
| **Skipped** | **15** (all: `TEST_DATABASE_URL or DATABASE_URL is not set`) |
| **Failed** | **0** |
| Duration | ~24s |

## Postgres re-run attempt

With `TEST_DATABASE_URL=postgresql+psycopg://hmore:hmore@localhost:5432/hmore_test`:

| Result | Count |
| --- | ---: |
| Passed | 55 |
| Errors | 15 (connection refused — Postgres unavailable) |
| Failed | 0 |

## Web typecheck

| Command | Result |
| --- | --- |
| `apps/web` `npm run typecheck` | **NOT RUN** — no web source changes in Prompt 6 verification |

## M13 — Enterprise analytics (Task 6)

`test_f62_reports_analytics.py` included above: **5 passed, 1 skipped** (`test_occupancy_plans_schedules_alerts_isolation` needs Postgres). Module uses `app.reporting.*` services against ORM models — **not** static demo JSON.

## Mobile

Not in Prompt 6 scope.

## Honest verdict

- **Offline pytest subset: PASS** (0 failures among executed tests).
- **Postgres integration: UNVERIFIED** this session — do not claim full F2.13/F6.1/M14 DB PASS without Docker + `hmore_test`.