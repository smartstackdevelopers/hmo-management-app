# PROMPT 3 — Test report (implementation pass)

**Date:** 2026-11-14

---

## Summary

| Suite | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| API full pytest | **415** | **0** | 117 |
| M02/M04/M05 + journeys subset | **45** | **0** | 16 |
| Mobile Jest (`tenantMobile` \| `staffMobile`) | **25** | **0** | 0 |
| Web `npm run typecheck` | **PASS** | — | — |

---

## New / updated tests

| Test | Proves |
| --- | --- |
| `test_tenant_own_profile_needs_goals_isolated_per_login` | M02.2 cross-tenant isolation on self API |
| `test_f21` unassigned `create_handover` | M04.3 RBAC |
| `tenantMobile` / `staffMobile` | Patch whitelist + handover client guard |

---

## Journeys A–D

| Journey | Status |
| --- | --- |
| A — Tenant self (incl. needs_goals) | **PASS** (pytest) |
| B — Caseload / logs / handovers | **PASS** |
| C — Support plan lifecycle | **PASS** |
| D — `test_f215_ali_end_to_end` | **PASS** |

Auth0 E2E: **UNVERIFIED**.

---

## Commands run

```powershell
cd apps\api; python -m pytest -q
cd apps\api; python -m pytest -q tests/test_f21_*.py ... test_f215_ali_end_to_end.py
cd room-ready; npm test -- --testPathPattern="tenantMobile|staffMobile"
cd apps\web; npm run typecheck
```