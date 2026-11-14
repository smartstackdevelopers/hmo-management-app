# PROMPT 3 — Staff management (M04) audit

**Date:** 2026-11-14  
**Scope:** M04.1–M04.6

---

## Module summary

| Metric | Value |
| --- | ---: |
| Features | 6 |
| **PASS** (verified) | **6** |
| **Verified completion** | **100%** |

---

## Feature matrix

| ID | Feature | Status | Web | Mobile | API | Tests | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M04.1 | Caseload | **PASS** | support-worker | `caseload.ts` | `/caseload` | `test_f21_*` | **PASS** |
| M04.2 | Daily logs | **PASS** | daily-logs | `dailyLogs.ts` | `/daily-logs` | `test_f21_*` | **PASS** |
| M04.3 | Handovers | **PASS** | handovers pages | `handovers.ts`, `HandoverBoard`, `staff/handovers` | `/handovers` | `test_f21` + `test_unassigned_handover_create` | **PASS** |
| M04.4 | Rota / visits / tasks | **PASS** | rota, visits, tasks | staff services | `ops.py` | `test_f22_*` | **PASS** |
| M04.5 | Training / safeguarding | **PASS** | training, safeguarding | alerts service | `compliance.py` | `test_f23_*` | **PASS** |
| M04.6 | Incidents & workload | **PASS** | incidents, workload | `incidents.ts` | `incidents.py` | `test_f24_*` | **PASS** |

---

## M04.3 implementation

- **Client:** `room-ready/lib/hmore/services/staff/handovers.ts` — `GET/POST /handovers` via `hmoreFetch`, `assertCanUseCaseload`.
- **UI:** `HandoverBoard.tsx` — list (pending or per-tenant), create with summary/priority/submit; loading/error via React Query; links from `CaseDetail` and `StaffMore`.

No new API routes (existing `apps/api/app/api/v1/support.py` handover router).

---

## Security (executed)

| Check | Evidence |
| --- | --- |
| Unassigned worker handover create | `test_f21_support_caseloads.py` (403 before assignment) |
| Unassigned caseload | `test_rbac_authorization.py` |
| Cross-org caseload | `test_caseload_logs_handovers_isolation` |

---

## Files changed (this pass)

`room-ready/lib/hmore/services/staff/handovers.ts`, `components/staff/HandoverBoard.tsx`, `app/(app)/staff/handovers.tsx`, `_layout.tsx`, `StaffMore.tsx`, `CaseDetail.tsx`, `__tests__/staffMobile.test.ts`, `apps/api/tests/test_f21_support_caseloads.py`.

---

## Journey B (automated)

`test_f21_support_caseloads` handover lifecycle — **PASS**. Auth0 web/mobile E2E — **UNVERIFIED**.