# PROMPT 5 — Test report

**Date:** 2026-11-14  
**Environment:** Windows, Python 3.12; **PostgreSQL/Docker not running** (connection errors to `localhost:5432`).

## Summary

| Suite | Passed | Failed | Skipped | Errors | LLM mode |
| --- | ---: | ---: | ---: | ---: | --- |
| `apps/ai-service` (full) | **84** | 0 | 2 | 0 | **MOCK** |
| API F3.x subset (no `DATABASE_URL`) | **9** | 0 | **33** | 0 | mock/heuristic |
| API F3.x subset (`hmore_test` URL set, PG down) | **22** | 0 | 0 | **34** | — |
| API unit (`test_f34_notes_analysis_unit`, `test_f315_ai_feature_flags_unit`) | **8** | 0 | 0 | 0 | mock |
| API `test_f54_job_matching` (unit subset) | **9** | 0 | 1 deselected | 0 | mock patch |
| API `test_f55_wellbeing::test_alembic_head_is_f55` | **1** | 0 | 0 | 0 | n/a |
| Full `apps/api` pytest | — | — | — | — | **NOT RUN** (no PG) |
| Web typecheck | — | — | — | — | **NOT RUN** (web untouched) |
| Live `/api/v1/ai-*` HTTP smoke | — | — | — | — | **UNVERIFIED** |

**Aggregate offline green:** ai-service **84** + API unit/offline **~27** (overlap: subset includes some unit tests) → treat as **≥93 automated assertions green** without database.

---

## Commands run

```powershell
cd apps\ai-service; python -m pytest -q
# 84 passed, 2 skipped

cd apps\api; python -m pytest -q tests/test_f34_notes_analysis.py ... test_f54_job_matching.py
# No DATABASE_URL: 9 passed, 33 skipped

$env:DATABASE_URL="postgresql+psycopg://hmore:hmore@localhost:5432/hmore_test"
$env:TEST_DATABASE_URL=$env:DATABASE_URL
cd apps\api; python -m pytest -q (same subset)
# 22 passed, 34 errors (PG unreachable)

cd apps\api; python -m pytest -q tests/test_f34_notes_analysis_unit.py tests/test_f315_ai_feature_flags_unit.py
# 8 passed

cd apps\api; python -m pytest -q tests/test_f54_job_matching.py -k "not flow_and_isolation"
# 9 passed
```

---

## Postgres-marked tests (require `hmore_test`)

Skipped when `TEST_DATABASE_URL` unset; error when URL set but server down:

| File | Focus |
| --- | --- |
| `test_f33_ai_usage_caps.py` | Budget reserve, hard cap, idempotency |
| `test_f34_notes_analysis.py` | Analyse + review + isolation |
| `test_f35_case_summaries.py` | Generate + invalid AI + budget |
| `test_f36_document_checks.py` | PDF check + AI failure handling |
| `test_f37_support_plan_drafts.py` | Draft approval path |
| `test_f38_housing_application_analysis.py` | No mutation / no auto reject |
| `test_f39_compliance_agent.py` | Sweep without auto-resolve |
| `test_f310_tenant_assistant.py` | Grounded answers |
| `test_f311_duplicate_detection.py` | Rule-based duplicates |
| `test_f312_operational_search.py` | Org-scoped search |
| `test_f313_report_drafts.py` | Draft + dedupe |
| `test_f314_ai_activity.py` | Activity feedback |
| `test_f315_ai_feature_flags.py` | Flag enforcement |
| `test_f55_wellbeing.py` | Wellbeing flow |
| `test_f54_job_matching.py::test_job_matching_flow_and_isolation` | Full flow |

**To reach LOCAL PASS on tests:** start Docker Postgres, `alembic upgrade head` on `hmore_test`, re-run subset or full `pytest -q` per `PROMPT_1_TEST_REPORT.md`.

---

## ai-service skips (2)

Typically integration cases when optional deps or env not set — all core workflow tests **passed** with mock LLM.

---

## Auth0 / browser

Dashboard AI panels not exercised in live browser; marked **UNVERIFIED** per Prompt 5 rules.