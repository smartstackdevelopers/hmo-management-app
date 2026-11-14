# PROMPT 5 — AI architecture report

**Date:** 2026-11-14  
**Branch:** `develop` (pre-commit audit; see coordinator summary for commit hash)  
**Scope:** `apps/ai-service`, API AI proxies, billing path, LangGraph workflows. No `.env` secrets read. No DB reset.

## Overall verdict

| Area | ID | Status | Notes |
| --- | --- | --- | --- |
| Standalone AI service (F3.1–F3.2) | F3.1 | **PASS** (code + pytest) | Single service `apps/ai-service`; no duplicate gateway in `apps/api` |
| LangGraph runtime + workflows | F3.2 | **PASS** | `app/graph/runtime.py` — 14 workflows registered |
| Core API budget / usage (single path) | F3.3 | **PARTIAL** | `apps/api/app/api/v1/ai_usage.py` + ai-service `budget/client.py`; postgres caps tests **UNVERIFIED** (no PG) |
| Prompt store / routing / cache / batch | F3.2 | **PASS** | ai-service `prompts/`, `routing/`, `cache/`, `batch/` + tests |
| API → ai-service proxy pattern | F3.x | **PASS** | Per-feature `*/ai_client.py` → `POST /api/v1/workflows/execute` |
| Live OpenAI / external LLM | — | **LOCAL MOCK** | Default tests use `LLM_PROVIDER=mock` or monkeypatched clients |
| Live stack (API :8000 + ai-service) | — | **UNVERIFIED** | Servers not run in this audit |

---

## Service topology

```text
apps/web / room-ready  →  apps/api (Auth0, RLS, org context)
                              ↓ httpx + AI_SERVICE_TOKEN
                         apps/ai-service (/api/v1/workflows/execute)
                              ↓ reserve_budget → apps/api /internal/ai/*
                         LangGraph graphs + MockLlmProvider | openai_compat
```

| Component | Path | Role |
| --- | --- | --- |
| AI service entry | `apps/ai-service/app/main.py` | FastAPI, v1 router |
| Workflow dispatch | `apps/ai-service/app/graph/runtime.py` | Budget reserve, approval gate, execute graph |
| Budget client | `apps/ai-service/app/budget/client.py` | Calls core API; fail-open only when `budget_enforcement_fail_open` |
| Usage API | `apps/api/app/api/v1/ai_usage.py` | `reserve`, `reconcile`, budgets, internal token guard |
| Feature IDs | `apps/api/app/ai_usage/features.py` | Canonical `FEATURE_*` map for agents |
| Config | `apps/api/app/core/config.py` | `AI_SERVICE_BASE_URL`, `AI_SERVICE_TOKEN` (env only) |

**Rules checked:** No hardcoded API keys in repo; no second AI microservice; caps route through `ai_usage` (not bypassed in reviewed clients).

---

## LangGraph workflows (`SUPPORTED_WORKFLOWS`)

| workflow_id | API consumer (examples) | feature_id (via `feature_for_workflow`) |
| --- | --- | --- |
| `notes_analysis` | `notes_analysis/ai_client.py` | `ai.agent.notes_analysis` |
| `case_summary` | `case_summaries/ai_client.py` | `ai.workflow.case_summaries` |
| `document_check` | `document_checks/ai_client.py` | `ai.workflow.document_checker` |
| `support_plan_draft` | `support_plan_drafts/ai_client.py` | `ai.agent.support_planning` |
| `housing_application_analysis` | `housing_application_analysis/ai_client.py` | `ai.agent.housing_application` |
| `compliance_explanation` | `compliance_agent/ai_client.py` | `ai.agent.compliance` |
| `tenant_assistant` | `tenant_assistant/ai_client.py` | `ai.agent.tenant_assistant` |
| `job_match_explain` | `job_matching/ai_client.py` | `ai.agent.job_matching` |
| `operational_search` | `operational_search/ai_client.py` | `ai.workflow.operational_search` |
| `report_draft_narrative` | `report_drafts/ai_client.py` | `ai.workflow.report_draft` |
| `daily_log_rewrite` | `daily_log_rewrite/ai_client.py` | `ai.workflow.daily_log_rewrite` |
| `foundation_*` | Health / routing tests | infra features |

Graph sources: `apps/ai-service/app/graph/*.py`. Approval: `app/approval/service.py` (human gate on `require_human_gate`).

---

## API routers (v1)

Registered in `apps/api/app/api/v1/router.py`:

| Prefix | Module | Agent / feature |
| --- | --- | --- |
| `/notes-analysis` | `notes_analysis.py` | F3.4 |
| `/support-plan-drafts` | `support_plan_drafts.py` | F3.7 |
| `/housing-application-analyses` | `housing_application_analysis.py` | F3.8 |
| `/compliance-agent` | `compliance_agent.py` | F3.9 |
| `/tenant-assistant` | `tenant_assistant.py` | F3.10 |
| `/ai` + `/internal/ai` | `ai_usage.py` | F3.3 billing |
| `/ai-feature-flags` | `ai_feature_flags.py` | F3.15 |
| `/ai-activity` | `ai_activity.py` | transparency |
| `/employment`, `/job-matching` | F5.3 / F5.4 | Job agent + embeddings |

---

## LLM provider mode (this audit)

| Mode | When | Status |
| --- | --- | --- |
| **MOCK** | `LLM_PROVIDER=mock`, pytest defaults | **PASS** — 84 ai-service tests |
| **Heuristic fallback** | API services when `AI_SERVICE_BASE_URL` empty | **PASS** — by design (e.g. housing checklist narrative) |
| **Real LLM** | `openai_compat` + live keys in env | **UNVERIFIED** — not exercised |

---

## M11.3 note

Push/email/SMS remains **LOCAL MOCK** per `HMORE_FEATURE_LOCAL_100_PLAN.md`; AI architecture does not duplicate notification providers.

---

## Tests

| Suite | Result |
| --- | --- |
| `apps/ai-service` full pytest | **84 passed**, 2 skipped, 0 failed |
| API postgres-marked F3.x | **Skipped** without `DATABASE_URL`; **errors** when URL set but Postgres down |

See `PROMPT_5_TEST_REPORT.md`.