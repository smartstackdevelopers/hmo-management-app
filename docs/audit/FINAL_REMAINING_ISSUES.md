# FINAL — Remaining issues (Prompt 7)

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Git | `f3097b2` |
| Gate | **NOT ACHIEVED** |

## P0 — Blocks LOCAL 100%

| ID | Issue | Action |
| --- | --- | --- |
| G1 | **2/56** strict LOCAL PASS (need ≥50) | Execute Auth0 E2E per `ROLE_ACCEPTANCE_CHECKLIST.csv` |
| G2 | Mandatory **M01, M03, M08, M04, M10.1, M10.2** not proven | Module smoke with demo org |
| G3 | **Six roles** login | `bootstrap-all-six-roles.ps1` + browser/mobile |
| G4 | **Six AI** dashboards no-500 smoke | Auth0 session + API running |
| G5 | **117 pytest skips** | Start Docker; `hmore_test` + `alembic upgrade head`; re-run until skip count matches CI |

## P1 — High value

| ID | Issue |
| --- | --- |
| M10.1 | Super Admin org UI — **wired** but **browser UNVERIFIED** |
| M05.2 | Support plan export PDF download not browser-tested |
| M13.3 | Redis/Celery schedules — accepted **MOCK** until P5 done |
| Playwright | Optional regression pack not run |

## P2 — Accepted MOCK/DEFER (plan)

| ID | Status |
| --- | --- |
| M11.3 | MOCK — comms providers |
| M12.4 | MOCK — e-sign baseline |
| M13.3 | MOCK — schedules without Redis |
| M14.2 | MOCK — manual occupancy |
| M14.3 | **DEFER** — live camera |

## P3 — Production (explicitly out of scope)

AWS, stores, Go-Live — per user instruction **not started**.

## Resolved in Prompt 7 session

| Item | Resolution |
| --- | --- |
| Dirty Prompt 3 tree | Committed `f3097b2` |
| M10.1 UI stub (stale audit) | **UI exists** — status → PARTIAL |
| Mobile 3001 default (stale) | **Removed** in current `config.ts` |
| Local pytest hard failures | **0 failures** this run |