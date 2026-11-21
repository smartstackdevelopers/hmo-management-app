# PROMPT 6 — Landlord enterprise (F6.1)

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Branch | `develop` @ `60b2f02` |

## Summary

| Criterion | Status |
| --- | --- |
| Web `dashboard/landlord` | **PARTIAL** — `LandlordEnterpriseClient` calls `landlordEnterpriseApi` (dashboard, portfolio, rent ledger, inspections, repairs) |
| Rent ledger (no payment gateway) | **PASS** (unit) — `LEDGER_DISCLAIMER` / `test_ledger_disclaimer_is_non_payment_gateway` |
| Portfolio RBAC | **PASS** (unit) — landlord has `PROPERTIES_MANAGE`, `RENT_RECORDS_MANAGE`, `INSPECTIONS_MANAGE`; tenant denied |
| Cross-org isolation | **UNVERIFIED** — `test_landlord_enterprise_flow_and_isolation` **skipped** (no Postgres) |

**F6.1 completion:** **~70%** (UI + RBAC unit **PASS**; DB flow **UNVERIFIED**).

## Evidence

| Asset | Location |
| --- | --- |
| API module | `apps/api/app/landlord_enterprise/` |
| Web client | `apps/web/src/lib/landlordEnterpriseApi.ts` |
| Page | `apps/web/src/app/dashboard/landlord/page.tsx` |

## Tests

```powershell
cd apps\api
.\.venv\Scripts\pytest -q tests/test_f61_landlord_enterprise.py
```

| Passed | Skipped | Failed |
| ---: | ---: | ---: |
| 5 | 1 | 0 |

Skipped: `test_landlord_enterprise_flow_and_isolation` (`@pytest.mark.postgres`).

## Rules compliance

- **No finance/payment gateway** — ledger status tracking only; disclaimer tested.
- Contractor marketplace — not implemented as mandatory core (Task 10).

## Gaps

- Start Docker Postgres + re-run F6.1 integration test.
- Auth0 landlord role browser smoke on `/dashboard/landlord`.