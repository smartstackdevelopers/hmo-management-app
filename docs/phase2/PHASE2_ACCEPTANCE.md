# Phase 2 acceptance checklist

Evidence from `develop` at F2.15 handoff. **Synthetic Ali journey** is the acceptance anchor for F2.15.

## Feature table

| ID | Feature | Merged PR | Automated tests | Acceptance |
|----|---------|-----------|-----------------|------------|
| F2.1 | Support caseloads, logs, handovers | #15 | `test_f21_support_caseloads.py` | PASS (merged + tests) |
| F2.2 | Rota, visits, tasks, reminders | #16 | `test_f22_*` | PASS |
| F2.3 | Training & safeguarding | #17 | `test_f23_*` | PASS |
| F2.4 | Incidents, follow-ups, workload | #18 | `test_f24_*` | PASS |
| F2.5 | Housing applications | #19 | `test_f25_*` | PASS |
| F2.6 | Evidence packs | #20 | `test_f26_*` | PASS |
| F2.7 | Complaints | #21 | `test_f27_*` | PASS |
| F2.8 | Maintenance | #22 | `test_f28_*` | PASS |
| F2.9 | Tenant timeline | #23 | `test_f29_*` | PASS |
| F2.10 | Support plans | #24 | `test_f210_*` | PASS |
| F2.11 | Documents | #25 | `test_f211_*` | PASS |
| F2.12 | Communication | #26 | `test_f212_*` | PASS (providers default mock) |
| F2.13 | Org workflows | #27 | `test_f213_*` | PASS |
| F2.14 | Reports | #28 | `test_f214_*` | PASS |
| F2.15 | Ali E2E (no AI) | (this PR) | `test_f215_ali_end_to_end.py` | PASS\* |

\*F2.15 postgres integration test **skipped** without `TEST_DATABASE_URL`; unit + definition tests always run.

## Phase 2 exit criteria

| Criterion | Status |
|-----------|--------|
| Ali scenario without AI | **PASS** (documented + service-level test when PG available) |
| Module integration | **PASS** (F2.1→F2.8→F2.13→F2.14 in Ali test) |
| All Phase 2 scopes demoable | **NOT VERIFIED** in one UI session (see per-feature table) |
| Email/SMS/in-app paths exist | **PASS** (F2.12; real delivery **NOT VERIFIED** without provider config) |
| Push notifications | **N/A** (deferred per plan) |
| No silent authz failures | **PASS** (journey test asserts 403) |
| RBAC enforced | **PASS** (journey + existing suites) |
| Organisation isolation | **PASS** (journey cross-org check) |
| Audit trails | **PASS** (journey asserts maintenance + daily log audits) |
| Regression tests | **PASS** (full pytest green offline) |

## Final decision

**PHASE 2 ACCEPTANCE NOT VERIFIED** for full production sign-off until:

1. `TEST_DATABASE_URL` run completes `test_f215_ali_journey_full_human_workflow`.
2. Staging manual walkthrough of Ali UI guide (`/dashboard/journeys/ali`).
3. Optional: live SMTP/Twilio verification for F2.12 (out of F2.15 scope).
