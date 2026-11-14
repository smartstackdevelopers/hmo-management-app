# PROMPT 5 — Remaining issues

**Date:** 2026-11-14  
**Branch:** `develop`

## Blocking for LOCAL PASS (AI module)

| Priority | Issue | Action |
| --- | --- | --- |
| P0 | PostgreSQL not running locally | Start Docker Postgres; create `hmore_test`; `alembic upgrade head` |
| P0 | 34 F3.x / F5.5 integration tests errored (socket) | Re-run Prompt 5 pytest subset after PG up |
| P1 | Full API pytest not re-run this sprint | `cd apps\api; python -m pytest -q` on `hmore_test` |

## UNVERIFIED (not failures)

| Item | Notes |
| --- | --- |
| Live LLM (`LLM_PROVIDER=openai_compat`) | Use env keys only; confirm reconcile + caps |
| ai-service + API both on `:8000` / ai port | Smoke `GET /api/v1/ai/...` with Auth0 token |
| Auth0 browser on six AI dashboards | notes-analysis, support-plans, housing, compliance, tenant-assistant, ai-costs |
| Mobile tenant assistant + employment AI | Expo against local API |

## Code / architecture — no change required this pass

Inspection found:

- Single `apps/ai-service` gateway  
- Dashboard panels call real API clients (no demo stubs in scoped paths)  
- No hardcoded provider keys  
- Housing AI does not auto-decide applications  

## Environment checklist (from `.env.example` only)

- `AI_SERVICE_BASE_URL`, `AI_SERVICE_TOKEN` (api + ai-service)  
- `CORE_API_BASE_URL` on ai-service for budget enforcement (not fail-open)  
- `TEST_DATABASE_URL` for CI-parity local tests  

## Excluded from commit (per Prompt 5)

- `scripts/meeting-demo.local.env`  
- `docs/**/*.pdf`, `docs/audit/_pdf_export/`  
- Unrelated Prompt 3 working tree edits (support/caseload/mobile)

## Prompt 6

**Out of scope** — do not start production deploy or Prompt 6 work per user instruction.

---

## Status roll-up (requirements)

| Verdict | Count (approx.) | Definition |
| --- | ---: | --- |
| **PASS** | 12 | Code + offline tests green |
| **PARTIAL** | 14 | Architecture present; PG or live LLM pending |
| **FAIL** | 0 | No failing assertions when DB absent (errors = env) |
| **UNVERIFIED** | 8 | E2E, live LLM, full API suite, HTTP smoke |