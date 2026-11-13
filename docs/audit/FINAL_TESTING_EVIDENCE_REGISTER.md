# Final testing evidence register

**Audit date:** 2026-11-12  
**Primary automation:** GitHub Actions `.github/workflows/ci.yml`

## API (Pytest)

| Suite | Evidence | Local run (2026-11-12) |
| --- | --- | --- |
| Full API `-m "not postgres"` | `apps/api/tests/test_*.py` | **326 passed**, 1 skipped, 110 postgres deselected |
| Postgres-marked | `-m postgres` | **CI** — requires service container |
| Phase 6 | `test_f61`–`test_f68` | Included above |
| Phase 7 | `test_f72`–`test_f79`, `test_f74`, `test_f78` | Included / dedicated |
| RBAC six roles | `test_rbac_registry.py::test_exactly_six_approved_roles` | PASS |
| Ali E2E | `test_f215_ali_end_to_end.py` | PASS (non-postgres) |

## AI service

| Suite | Evidence |
| --- | --- |
| `apps/ai-service/tests/` | CI job **AI service** — green on PR |

## Web

| Suite | Evidence |
| --- | --- |
| Playwright e2e | CI job **Web** — health, accessibility (`e2e/accessibility.spec.ts`) |
| F7.5 axe | 7 passed per F7.5 report |

## Mobile

| Suite | Evidence |
| --- | --- |
| `room-ready` typecheck | CI **Mobile typecheck** |
| `npm run test:release` | F7.7 — 5 passed (release prep) |
| Mobile a11y | F7.5 per F7.7/5 reports |

## Infrastructure / ops docs

| Test | Evidence |
| --- | --- |
| `test_f76_infrastructure.py` | F7.6 Terraform files |
| `test_f78_training.py` | Training doc presence |
| `test_f79_runbooks.py` | Runbook doc presence |
| `test_f710_coverage_audit.py` | Audit package presence |

## Not claimed

- Production load test on live AWS
- Physical device store acceptance
- Organisational UAT sign-off
- Penetration test report

## Test inventory count

**72** files matching `apps/api/tests/test_f*.py` (+ core tests `test_health`, `test_rbac_*`, etc.).
