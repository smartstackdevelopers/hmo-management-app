# Final end-to-end acceptance testing record

**Environment:** Local / CI test harness — **not production**.  
**Execution date:** 2026-11-12

| # | Workflow | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Login (test client) | **PASS** | Auth tests, web e2e health |
| 2 | Tenant onboarding | **PARTIAL** | `test_f16_records.py` |
| 3 | Housing application | **PASS** | `test_f25_housing_applications.py` |
| 4 | Application review | **PASS** | `test_f213_org_workflows.py` |
| 5 | Property assignment | **PARTIAL** | housing + property tests |
| 6 | Support plan | **PASS** | `test_f210_support_plans.py` |
| 7 | Daily notes | **PASS** | `test_f21_support_caseloads.py` |
| 8 | Maintenance | **PASS** | `test_f28_maintenance.py` |
| 9 | Complaints | **PASS** | `test_f27_complaints_workflow.py` |
| 10 | Document upload | **PASS** | `test_f211`, `test_f18` |
| 11 | AI assistance | **PARTIAL** | Phase 3 tests |
| 12 | Landlord dashboard | **PASS** | `test_f61_landlord_enterprise.py` |
| 13 | Reports / exports | **PARTIAL** | `test_f62`, `test_f214` |
| 14 | Automation | **PARTIAL** | `test_f63` |
| 15 | Notifications | **PARTIAL** | `test_f43`, `test_f212` |
| 16 | Mobile sync | **PASS** | `test_f45_offline_sync.py` |
| 17 | Role permissions | **PASS** | `test_rbac_*` |
| 18 | Organisation isolation | **PARTIAL** | postgres tests in CI |

**Combined journey:** `test_f215_ali_end_to_end.py` — **PASS** (automated).

Production re-run required after deploy (see `docs/phase7/production/SMOKE_TEST_SCRIPT.md`).
