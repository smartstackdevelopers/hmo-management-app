# PROMPT 6 — Security (six roles, cross-org)

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Branch | `develop` @ `60b2f02` |
| Builds on | `docs/audit/PROMPT_2_SECURITY_TEST_REPORT.md` |

## Summary

| Area | Status | This session |
| --- | --- | --- |
| Six roles registry | **PASS** | `test_rbac_registry.py` — 9 passed |
| Cross-org denial (Postgres) | **UNVERIFIED** | 7 tests **skipped** — Docker/Postgres offline |
| Cross-org / workflow unit | **PASS** | `test_f213` schema tests; postgres isolation skipped |
| New seventh role | **N/A** | Not introduced (per prompt rules) |

**Security extension:** **None required** — no gap found that needs new tests beyond prior Prompt 2 work; Postgres-marked tests deferred for environment.

## Tests executed (subset)

```powershell
cd apps\api
.\.venv\Scripts\pytest -q tests/test_rbac_registry.py tests/test_organisation_isolation.py
```

| File | Passed | Skipped | Failed |
| --- | ---: | ---: | ---: |
| `test_rbac_registry.py` | 9 | 0 | 0 |
| `test_organisation_isolation.py` | 4 | 7 | 0 |

## Posture

- Org workflows, landlord enterprise, room occupancy modules include cross-org tests behind `@pytest.mark.postgres` — run when `TEST_DATABASE_URL` available.
- Live Auth0 browser IDOR — **UNVERIFIED** (unchanged from Prompt 2).

## Mandatory exclusions

Production deploy, cameras, seventh role — **not** in scope.