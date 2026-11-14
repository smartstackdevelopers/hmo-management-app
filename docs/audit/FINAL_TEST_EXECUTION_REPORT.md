# FINAL — Test execution report (Prompt 7)

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Git | `f3097b2` |
| Environment | Windows; Docker **unavailable** at audit start |

## API — pytest

```text
cd apps/api
..\..\ .venv\Scripts\pytest -q
→ 415 passed, 117 skipped, 0 failed (~59s)
```

| Note | Detail |
| --- | --- |
| Skips | Primarily postgres/socket/integration markers when DB unreachable |
| Prior failure | `test_upgrade_downgrade_roundtrip` — **not failed** this run |
| Targeted P3 | `test_f21_support_caseloads.py` + `test_f41_tenant_mobile.py` → 9 pass, 6 skip |

**Env:** `TEST_DATABASE_URL` / `hmore_test` — **partial** (suite ran with skips, not full DB parity).

## Web

| Command | Result |
| --- | --- |
| `npm run typecheck` | **PASS** |
| `npm run build` | **PASS** (Auth0 dpop critical dependency warning) |

## Mobile (room-ready)

| Command | Result |
| --- | --- |
| `npm test` (full jest) | **70 passed**, 0 failed |
| P3 subset `staffMobile\|tenantMobile` | **25 passed** |

## E2E

| Tool | Result |
| --- | --- |
| Playwright `test:e2e` | **UNVERIFIED** — not executed (would need stack + Auth0) |

## CI comparison

| Source | Status |
| --- | --- |
| GitHub `develop` post PR #112 | Reported green (Prompt 1) — **not re-triggered** in Prompt 7 |

## Verdict

**Zero test failures** in executed suites; **full DB pytest parity NOT proven** due to skips.