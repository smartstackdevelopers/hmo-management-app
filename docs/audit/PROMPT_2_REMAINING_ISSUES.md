# PROMPT 2 — Remaining issues

**Date:** 2026-11-14  
**Prompt 3:** Not started (per scope).

---

## Overall gate (auth & roles module)

| Item | Verdict |
| --- | --- |
| M01.1 Six roles enforced (code) | **PASS** |
| M01.2 Auth0 login/logout (live) | **PARTIAL** |
| M01.3 Org isolation (automated) | **PASS** |
| M01.6 MFA staff path | **UNVERIFIED** |
| Six-role acceptance checklist | **UNVERIFIED** |

---

## Must verify manually (blocks LOCAL PASS)

1. **Auth0 tenant** — Populate `apps/api/.env`, `apps/web/.env.local`, `room-ready/.env` from `.env.example` templates; shared `AUTH0_AUDIENCE`.
2. **Six users** — Create users in Auth0; copy `scripts/meeting-six-roles.env.example` → gitignored `meeting-six-roles.local.env`; run `.\scripts\bootstrap-all-six-roles.ps1`.
3. **ROLE_ACCEPTANCE_CHECKLIST.csv** — Complete R1–R6 with tester/date.
4. **MFA** — Follow `docs/development/MFA_CONFIGURATION.md`; then optionally set `AUTH0_REQUIRE_MFA_CLAIM=true` after confirming `amr` on access tokens.
5. **Super Admin org UI** — Auth0 login + `PLATFORM_GOVERNANCE_GLOBAL_ENABLED=true`; `/dashboard/super-admin/organisations`.

---

## Known code / product gaps (not fixed in Prompt 2)

| Issue | Severity | Verdict |
| --- | --- | --- |
| Web nav not fully role-gated per route | Medium | **PARTIAL** — API is source of truth |
| Mobile `legacy` auth mode when Auth0 unset | Low | **PARTIAL** — intentional dev fallback |
| `test_organisations_list.py` was broken at P1 commit | Low | **FAIL** at collection → fixed locally (uncommitted) |
| Stash `prompt1-critical-fixes` still listed | Info | Changes already on `develop` @ `0ae8d07`; stash can be dropped |
| Playwright / Expo device smoke | Medium | **UNVERIFIED** |

---

## What Prompt 2 did not do

- No push to remote (user did not request).
- No commit for Prompt 2 audit docs or test fix (user did not request commit for P2).
- No AWS, production, or app-store publish.
- No duplicate auth system introduced.

---

## Suggested next (Prompt 3+, not executed)

- Commit audit quartet + test fix when ready.
- Run `npm run test:e2e` in `apps/web` after Auth0 env ready.
- Refresh `FEATURE_56_STATUS.csv` M01.2 / M01.6 after live smoke.