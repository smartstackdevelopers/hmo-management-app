# PROMPT 5 — AI cost control report (Task 9)

**Date:** 2026-11-14  
**IDs:** F3.3 usage caps, F3.15 feature flags, dashboard `ai-costs` / `ai-feature-flags`

## Overall verdict

| ID | Feature | Status | Notes |
| --- | --- | --- | --- |
| F3.3 | Org budgets, reservations, usage records | **PARTIAL** | Code **PASS**; `test_f33_*` postgres **UNVERIFIED** |
| F3.3 | Fail-closed hard cap | **PASS** (design) | API `BudgetExceededError` → 402; ai-service propagates |
| F3.3 | Single billing path | **PASS** | ai-service `reserve_budget` → API `/internal/ai/*` only |
| F3.15 | Per-org AI feature flags | **PARTIAL** | Unit tests **PASS**; isolation test needs PG |
| UI | AI costs dashboard | **PASS** (wiring) | `apps/web/.../ai-costs/page.tsx` — server fetch to API |
| UI | AI feature flags | **PASS** (wiring) | `AiFeatureFlagsPanel` → `/api/v1/ai-feature-flags` |

---

## Data model

| Table | Model file |
| --- | --- |
| `organisation_ai_budgets` | `db/models/ai_usage.py` |
| `ai_usage_records` | same |
| `ai_budget_reservations` | same |
| `ai_model_pricing` | same |
| `organisation_ai_feature_flags` | `db/models/ai_feature_flags.py` |
| `organisation_ai_feature_flag_history` | same |

---

## API surface

| Route | File | Purpose |
| --- | --- | --- |
| `/api/v1/ai/...` | `ai_usage.py` | Budget CRUD, usage dashboard aggregates, status |
| `/api/v1/internal/ai/reserve` | `ai_usage.py` | ai-service reservation (service token) |
| `/api/v1/internal/ai/reconcile` | `ai_usage.py` | Post-execution usage |
| `/api/v1/ai-feature-flags` | `ai_feature_flags.py` | Enable/disable features per org |

---

## ai-service enforcement

| Step | Path |
| --- | --- |
| Map workflow → feature | `app/budget/features.py` |
| Reserve before LLM | `app/graph/runtime.py` calls `reserve_budget` |
| Client | `app/budget/client.py` — fails if `CORE_API_BASE_URL` missing (unless explicit fail-open flag) |

Feature catalogue: `apps/api/app/ai_usage/features.py` (`FEATURE_NOTES_ANALYSIS`, …).

---

## Agent integration

Each agent client checks:

1. `require_feature_available` (F3.15) where applicable  
2. HTTP **402** from ai-service / budget client → surfaced to caller  
3. No alternate “free” LLM path bypassing reservation in reviewed clients  

Example: `job_matching/ai_client.py`, `notes_analysis` service when AI URL set.

---

## Tests

| File | Offline | Postgres |
| --- | --- | --- |
| `test_f33_ai_usage_caps.py` | — | **ERR** (PG down) |
| `test_f315_ai_feature_flags_unit.py` | **PASS** (subset) | — |
| `test_f315_ai_feature_flags.py` | — | **ERR** |
| ai-service `test_budget_client.py` | **PASS** (in 84 suite) | — |

---

## LOCAL MOCK vs real cost

| Mode | Cost accounting |
| --- | --- |
| `MockLlmProvider` | Usage metadata still emitted; tokens often null |
| Heuristic-only API paths | No ai-service call — no LLM spend |
| Live OpenAI | **UNVERIFIED** — pricing table + reconcile path not exercised live |