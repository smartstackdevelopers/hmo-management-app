# PROMPT 5 — Wellbeing (M09) report

**Date:** 2026-11-14  
**Module IDs:** M09.1 check-ins / routines; M09.2 directory / navigator (per `HMORE_FEATURE_LOCAL_100_PLAN.md`)

## Overall verdict

| ID | Feature | Status | Evidence |
| --- | --- | --- | --- |
| M09.1 | Check-ins, routines | **PARTIAL** | API `app/wellbeing/`; mobile `room-ready/app/(app)/wellbeing-*.tsx`; PG tests **UNVERIFIED** |
| M09.2 | Directory / resources | **PARTIAL** | Web `/dashboard/wellbeing-resources`; API directory endpoints |
| M09 disclaimer | Non-clinical copy | **PASS** | `app/wellbeing/constants.py` `DISCLAIMER`; web page notice |

---

## API

| Area | Path |
| --- | --- |
| Service | `apps/api/app/wellbeing/service.py` |
| Constants / disclaimer | `apps/api/app/wellbeing/constants.py` |
| Router | Registered via `apps/api/app/api/v1/router.py` (wellbeing module) |
| Tests | `apps/api/tests/test_f55_wellbeing.py` |

**Disclaimer (server):** States not medical service; crisis numbers (999 / Samaritans 116 123); moods not diagnoses.

---

## Web

| Route | File | API usage |
| --- | --- | --- |
| `/dashboard/wellbeing-resources` | `apps/web/src/app/dashboard/wellbeing-resources/page.tsx` | `WellbeingResourceAdminForm` (live API, not static demo) |
| Navigation | `apps/web/src/lib/navigation.ts` | Wellbeing entries |

Inline copy: *"HMore wellbeing tools are non-clinical. Do not present resources as medical treatment."*

---

## Mobile (`room-ready`)

| Screen | Path |
| --- | --- |
| Routines | `app/(app)/wellbeing-routines.tsx` |
| History | `app/(app)/wellbeing-history.tsx` |
| Client | `lib/hmore/services/wellbeing.ts` |
| Chart helper | `lib/hmore/wellbeingHistoryChart.ts` |

---

## Tests (this audit)

| Test | Result | Notes |
| --- | --- | --- |
| `test_alembic_head_is_f55` | **PASS** | Migration chain present |
| `test_wellbeing_flow_and_cross_tenant_denied` | **SKIPPED/ERR** | Requires PostgreSQL `hmore_test` — Docker not running |

---

## UNVERIFIED

- Live Auth0 browser flows for tenant wellbeing screens
- End-to-end mobile check-in against API `:8000`