# PROMPT 5 — Six agents report (F3.4–F3.10 + job matching)

**Date:** 2026-11-14  
**LLM in tests:** **MOCK** / monkeypatch / heuristic fallback — not live OpenAI.

## Summary

| # | Agent | Req ID | Dashboard / mobile | API prefix | Workflow | DB tables | Integration tests | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Notes Analysis | F3.4 | `/dashboard/notes-analysis` | `/api/v1/notes-analysis` | `notes_analysis` | `daily_log_ai_analyses`, `daily_log_ai_suggestions` | `test_f34_*` | **PARTIAL** (unit PASS; PG **UNVERIFIED**) |
| 2 | Support Planning | F3.7 | `/dashboard/support-plans` (+ drafts API) | `/api/v1/support-plan-drafts` | `support_plan_draft` | `support_plan_drafts` | `test_f37_*` | **PARTIAL** |
| 3 | Housing Application | F3.8 | `/dashboard/housing-applications/[id]` | `/api/v1/housing-application-analyses` | `housing_application_analysis` | `housing_application_analyses`, `housing_application_analysis_findings` | `test_f38_*` | **PARTIAL** |
| 4 | Compliance | F3.9 | `/dashboard/compliance-agent` | `/api/v1/compliance-agent` | `compliance_explanation` | `compliance_sweeps`, `compliance_findings` | `test_f39_*` | **PARTIAL** |
| 5 | Job Matching | F5.4 / F3 agent id | Mobile employment / API | `/api/v1/job-matching` | `job_match_explain` (+ local scoring/embeddings) | job_matching tables + embeddings helpers | `test_f54_*` (9 unit **PASS**) | **PARTIAL** |
| 6 | Tenant Assistant | F3.10 | `/dashboard/tenant-assistant` | `/api/v1/tenant-assistant` | `tenant_assistant` | `tenant_assistant_*` | `test_f310_*` | **PARTIAL** |

**Dashboard stubs:** No static demo data found; web pages call `*Api.ts` clients against `NEXT_PUBLIC_API_BASE_URL` (e.g. `notesAnalysisApi.ts`, `supportPlansApi.ts`).

---

## 1 — Notes Analysis (F3.4)

| Item | Detail |
| --- | --- |
| Service | `apps/api/app/notes_analysis/service.py` |
| AI client | `apps/api/app/notes_analysis/ai_client.py` |
| Human approval | Suggestion `approve` / `reject` / `dismiss` via API |
| Web disclaimer | Inbox copy: AI content not a verified staff statement |
| Offline tests | `test_f34_notes_analysis_unit.py` — **PASS** |
| Postgres workflow | `test_f34_notes_analysis.py` — requires `hmore_test` |

---

## 2 — Support Planning drafts (F3.7)

| Item | Detail |
| --- | --- |
| Service | `apps/api/app/support_plan_drafts/service.py` |
| Workflow | `support_plan_draft` |
| Responsible AI | Draft apply requires review; test name asserts no skip of approval |
| Web | `supportPlansApi.ts`, tenant + staff support plan routes |

---

## 3 — Housing Application analysis (F3.8)

| Item | Detail |
| --- | --- |
| Service | `apps/api/app/housing_application_analysis/service.py` |
| No auto decision | Analysis does not mutate `HousingApplication` / waiting list (`test_f38` docstring) |
| Fallback | Rule-based checklist + heuristic narrative when AI off; LLM optional |
| Web | `housing-applications/[id]` loads analysis via API |

---

## 4 — Compliance agent (F3.9)

| Item | Detail |
| --- | --- |
| Service | `apps/api/app/compliance_agent/` |
| Behaviour | Sweeps / explanations; tests assert no auto-resolve of training |
| Web | `ComplianceAgentPanel.tsx` → API |

---

## 5 — Job Matching (F5.4)

| Item | Detail |
| --- | --- |
| Scoring | `job_matching/scoring.py`, `embeddings.py` (local vectors; not cloud-only) |
| AI explain | Optional `explain_job_match` → ai-service with `require_human_gate: True` |
| Feature flag | `FEATURE_JOB_MATCHING` enforced in `ai_client.py` |
| Offline tests | Scoring, embeddings, import helpers — **9 passed** |

---

## 6 — Tenant Assistant (F3.10)

| Item | Detail |
| --- | --- |
| Service | `apps/api/app/tenant_assistant/` |
| Grounding | Tests require published announcements only |
| Pilot gating | Disabled when pilot env empty (`test_f310` cases) |
| Web | `TenantAssistantPanel.tsx` |

---

## Related F3 workflows (not “six agents” but same stack)

| Feature | ID | Tests |
| --- | --- | --- |
| Case summaries | F3.5 | `test_f35_*` |
| Document checker | F3.6 | `test_f36_*` |
| Operational search | F3.12 | `test_f312_*` |
| Report drafts | F3.13 | `test_f313_*` |
| Duplicate detection | F3.11 | `test_f311_*` |

All postgres-marked — **UNVERIFIED** this run (Postgres/Docker not available).