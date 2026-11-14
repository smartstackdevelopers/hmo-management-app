# PROMPT 3 — Staff management (M04) audit

**Date:** 2026-11-14  
**Branch:** `develop` @ `95bed7a`  
**Scope:** M04.1–M04.6 — caseload, daily logs, handovers, rota/visits/tasks, training/safeguarding, incidents/workload

---

## Module summary

| Metric | Value |
| --- | ---: |
| Features audited | 6 |
| **PASS** (verified by executed tests) | 5 |
| **PARTIAL** | 1 |
| **Verified completion** | **83%** |

---

## Feature matrix

| ID | Feature | Status | Web | Mobile | API | DB tables | Tests (executed) | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **M04.1** | Caseload | **PASS** | `/dashboard/support-worker` + `CaseloadClient` → `fetchCaseload`; `/dashboard/caseload/[tenantId]` | `staff/caseload.ts` → `/caseload`, case detail | `app/api/v1/support.py` (`caseload_router`) | `case_assignments`, `tenants` | `test_f21_support_caseloads.py::test_caseload_logs_handovers_isolation` | **PASS** |
| **M04.2** | Daily logs | **PASS** | `/dashboard/daily-logs/new` | `staff/dailyLogs.ts` → `POST/GET /daily-logs`; `DailyNoteEditor.tsx`, offline sync | `support.py` (`logs_router`) | `daily_logs` | Same F2.1 postgres flow + schema tests | **PASS** |
| **M04.3** | Handovers | **PARTIAL** | `/dashboard/handovers`, `/dashboard/handovers/new`, detail routes | Case detail lists `recent_handovers` only — **no** dedicated `POST /handovers` mobile service | `handovers_router` in `support.py` | `handovers` | F2.1 handover transition tests | **PASS** (API/web); **PARTIAL** (mobile create/list screens) |
| **M04.4** | Rota / visits / tasks | **PASS** | `/dashboard/rota`, `visits`, `tasks` | `staff/shifts.ts`, `visits.ts`, `tasks.ts` | `app/api/v1/ops.py` | shifts, visits, tasks tables (`support_ops` / ops models) | `test_f22_rota_visits_tasks.py::test_rota_visits_tasks_reminders_flow` | **PASS** |
| **M04.5** | Training / safeguarding | **PASS** | `/dashboard/training`, `/dashboard/safeguarding` | Safeguarding service under `staff/safeguardingAlerts.ts` | `app/api/v1/compliance.py` | compliance-related tables | `test_f23_training_safeguarding.py::test_training_and_safeguarding_flow` | **PASS** |
| **M04.6** | Incidents & workload | **PASS** | `/dashboard/incidents`, `/dashboard/workload` | `staff/incidents.ts` | `app/api/v1/incidents.py` | incidents / workload models | `test_f24_incidents_workload.py::test_incident_follow_up_workload_flow` | **PASS** |

---

## Security & caseload scope (executed)

| Check | Evidence | Result |
| --- | --- | --- |
| Unassigned worker denied | `tests/test_rbac_authorization.py::test_support_worker_cannot_access_unassigned_caseload` | **PASS** |
| Cross-org caseload isolation | `test_caseload_logs_handovers_isolation` | **PASS** |
| Contractor cannot read caseload | `test_f42_staff_mobile_unit.py::test_contractor_cannot_read_caseload_and_support_worker_cannot_decide` | **PASS** |
| Unauthenticated support APIs | `test_unauthenticated_support_apis_return_401` | **PASS** |

---

## Frontend wiring (web)

All listed dashboard routes use Auth0 token + organisation context and call HMore API helpers (`supportApi`, etc.). Loading and error patterns match Prompt 1 conventions (`EmptyState`, `ErrorState`). No fake success payloads observed.

---

## Mobile verification

| Area | HMore API | Notes |
| --- | --- | --- |
| Caseload tabs | **Yes** | `staffMobile.test.ts` asserts support_worker tab shell |
| Daily logs | **Yes** | POST with idempotency via `dailyLogs.ts` |
| Handovers | **Partial** | Read via case detail only |
| Visits / tasks / shifts | **Yes** | Dedicated service modules |
| Incidents | **Yes** | `staff/incidents.ts` |

Mobile Jest: `tenantMobile` + `staffMobile` — **24 passed**, 0 failed.

---

## Journey B — Support worker ops (automated)

| Step | Test module | Status |
| --- | --- | --- |
| Assign caseload → list | `test_f21_support_caseloads` | **PASS** |
| Create daily log | F2.1 postgres flow | **PASS** |
| Handover lifecycle | F2.1 submit → acknowledge → complete | **PASS** |
| Integrated Ali workflow (caseload note segment) | `test_f215_ali_end_to_end.py` (postgres) | **PASS** |

Auth0 E2E on web support-worker dashboard: **UNVERIFIED**.

---

## Remaining issues (M04)

1. Mobile handover create/list UI not wired to `/handovers` (web is complete).
2. Playwright dashboard E2E not run this sprint.
3. Live Auth0 support_worker caseload smoke: **UNVERIFIED**.