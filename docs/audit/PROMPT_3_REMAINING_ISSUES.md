# PROMPT 3 — Remaining issues

**Date:** 2026-11-14  
**Branch:** `develop`  
**Modules:** M02, M04, M05

---

## Verified LOCAL PASS rate (strict — automated evidence only)

| Module | PASS | Total | % |
| --- | ---: | ---: | ---: |
| **M02** Tenant management | 3 | 4 | **75%** |
| **M04** Staff management | 5 | 6 | **83%** |
| **M05** Support plans | 2 | 2 | **100%** |
| **Combined M02+M04+M05** | 10 | 12 | **83%** |

Features marked **PARTIAL** (not counted as PASS above):

| ID | Reason |
| --- | --- |
| M02.2 | Tenant mobile does not surface `needs_goals`; staff/timeline/support-plan APIs hold structured goals (by design). |
| M04.3 | Mobile lacks dedicated handover create/list; web + API complete. |

---

## Blocking manual verification

1. **Auth0 six-role smoke** — Caseload, support-plans dashboard, tenant mobile profile (`ROLE_ACCEPTANCE_CHECKLIST.csv`).
2. **Web export download** — M05.2 PDF from dashboard after login.
3. **Mobile handovers** — Product decision: add screen + service for `/handovers` or document web-only workflow.

---

## Code gaps (not fixed in Prompt 3 — no verified bugs)

| Issue | Severity | Notes |
| --- | --- | --- |
| Mobile handover UX | Low | API + web OK; mobile read-only on case detail |
| Tenant needs/goals on mobile | Low | Architectural — extend API or link to support-plan read |
| Playwright / Expo E2E | Medium | **UNVERIFIED** |
| Web typecheck this sprint | Info | Not re-run; no web diff |

No stub APIs, mock success, or RBAC weakening was applied.

---

## Carried from Prompt 2 (still open)

- Live Auth0 login/logout (M01.2) **PARTIAL**
- MFA staff path **UNVERIFIED**
- `meeting-demo.local.env` / pdf exports remain untracked (excluded from commit)

---

## Prompt 4

**Not started** (per coordinator scope).

---

## Suggested next actions

1. Add mobile `handovers.ts` + staff screen if mobile parity required for M04.3 LOCAL PASS.
2. Run `npm run typecheck` in `apps/web` after Auth0 env confirmed.
3. Optional: tenant-visible read-only goals from `/tenant/support-plans` (already on mobile) to close M02.2 perception gap.