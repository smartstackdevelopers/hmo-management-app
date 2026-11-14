# PROMPT 3 — Test report (M02 / M04 / M05)

**Date:** 2026-11-14  
**Environment:** Windows, Python 3.12, PostgreSQL (`TEST_DATABASE_URL` / `hmore_test` available)

---

## Executive summary

| Suite | Passed | Failed | Skipped | Verdict |
| --- | ---: | ---: | ---: | --- |
| API full pytest | **415** | **0** | 116 | **GREEN** |
| API M02/M04/M05 subset | **43** | **0** | 14 | **GREEN** |
| API journey extras | **9** | **0** | 1 | **GREEN** |
| Mobile Jest (`tenantMobile` \| `staffMobile`) | **24** | **0** | 0 | **GREEN** |
| Web typecheck / build | — | — | — | **Not run** (no web code changes) |
| Auth0 live E2E | — | — | — | **UNVERIFIED** |

---

## API pytest — full suite

```powershell
cd "D:\hmore app\apps\api"
python -m pytest -q
```

**Result:** 415 passed, 116 skipped, 1 warning (~58s)

Skip pattern: `@pytest.mark.postgres` and environment-gated tests when DB unavailable (on this machine most postgres tests **ran**).

---

## API pytest — M02 / M04 / M05 focused subset

```powershell
python -m pytest -q `
  tests/test_f21_support_caseloads.py `
  tests/test_f22_rota_visits_tasks.py `
  tests/test_f23_training_safeguarding.py `
  tests/test_f24_incidents_workload.py `
  tests/test_f29_tenant_timeline.py `
  tests/test_f210_support_plans.py `
  tests/test_f41_tenant_mobile.py `
  tests/test_f42_staff_mobile_unit.py `
  tests/test_rbac_authorization.py `
  tests/test_f37_support_plan_drafts.py `
  tests/test_f37_support_plan_drafts_unit.py
```

**Result:** 43 passed, 14 skipped (~52s)

### Highlights by module

| Module | File | Notable passing tests |
| --- | --- | --- |
| M04.1–4.3 | `test_f21_support_caseloads.py` | permissions, schemas, `test_caseload_logs_handovers_isolation` |
| M04.4 | `test_f22_rota_visits_tasks.py` | `test_rota_visits_tasks_reminders_flow` |
| M04.5 | `test_f23_training_safeguarding.py` | `test_training_and_safeguarding_flow` |
| M04.6 | `test_f24_incidents_workload.py` | `test_incident_follow_up_workload_flow` |
| M02.3 | `test_f29_tenant_timeline.py` | `test_timeline_and_meetings_isolation` |
| M05 | `test_f210_support_plans.py` | lifecycle + export + PDF unit |
| M02.1/4 | `test_f41_tenant_mobile.py` | self PATCH, housing, catalogues, documents |
| Security | `test_rbac_authorization.py` | unassigned caseload deny |

---

## Journey tests (A–D)

Interpretation aligned with Sprint S3 (staff + tenant journeys):

| Journey | Scope | Executed tests | Status |
| --- | --- | --- | --- |
| **A** | Tenant self profile / housing / own docs | `test_f41_tenant_mobile.py` (postgres cases) | **PASS** |
| **B** | Support caseload → daily log → handover | `test_f21_support_caseloads.py` (postgres) | **PASS** |
| **C** | Support plan goals → review → export | `test_f210_support_plans.py` | **PASS** |
| **D** | Tenant timeline + Ali integrated path | `test_f29_tenant_timeline.py`; `test_f215_ali_end_to_end.py` | **PASS** (1 skipped unit in f215 file when run alone: non-postgres markers only) |

```powershell
python -m pytest -q tests/test_f215_ali_end_to_end.py tests/test_f88_tenant_engagement.py
```

**Result:** 9 passed, 1 skipped (~10s)

**Auth0 E2E (all journeys):** **UNVERIFIED** — no live login in this audit.

---

## Mobile Jest

```powershell
cd "D:\hmore app\room-ready"
npm test -- --testPathPattern="tenantMobile|staffMobile" --silent
```

**Result:** 24 passed, 0 failed (~14s)

Covers: API base URL (`:8000`), tenant self PATCH field allow-list, staff caseload guard, role tabs, offline drafts, upload validation.

---

## Security subset (cross-org + tenant ownership)

Included in full suite and M02/M04 subset:

| Test | Proves |
| --- | --- |
| `test_caseload_logs_handovers_isolation` | Org-scoped caseload |
| `test_timeline_and_meetings_isolation` | Timeline IDOR |
| `test_f210_plan_lifecycle_and_isolation` | Support plan org boundary |
| `test_support_worker_cannot_access_unassigned_caseload` | Assignment RBAC |
| `test_tenant_can_patch_own_name_and_phone_only` | Tenant ownership |
| `test_housing_endpoint_returns_only_the_callers_assignment` | Tenant housing scope |

No new security tests were required; gaps documented in `PROMPT_3_REMAINING_ISSUES.md`.

---

## Not executed

- `apps/web` `npm run typecheck` / `npm run build`
- Playwright `apps/web/e2e`
- Expo on-device flows with Auth0
- Production deploy (out of scope)

---

## Pytest green for Prompt 3 scope?

**YES** — 0 failures on full suite and focused subsets listed above.