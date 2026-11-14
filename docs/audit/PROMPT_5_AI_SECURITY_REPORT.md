# PROMPT 5 — Responsible AI & security report (Task 10)

**Date:** 2026-11-14  
**Scope:** Human approval, activity logs, no autonomous housing decisions, service auth, org isolation. Complements Prompt 2 security work.

## Overall verdict

| Control | Status | Evidence |
| --- | --- | --- |
| Human approval before applying AI outputs | **PASS** (design + tests) | Notes suggestions, support plan drafts, report drafts (`auto_approved` false) |
| No auto housing approve/reject | **PASS** (code + F3.8 tests) | `housing_application_analysis` narrative only; decisions via separate housing service |
| AI activity transparency | **PARTIAL** | `ai_activity_logs` + `/api/v1/ai-activity`; PG tests **UNVERIFIED** |
| Service-to-service auth | **PASS** | `AI_SERVICE_TOKEN`, `require_ai_service_token` on internal AI routes |
| Org isolation on AI routes | **PASS** (claimed by tests) | Postgres cases in F3.4–F3.10 — **UNVERIFIED** locally |
| Trusted context in ai-service | **PASS** | `TrustedCallerContext`; body `organisation_id` not trusted |
| Privacy catalogue | **PASS** | `app/privacy/catalog.py` documents caps + human approval |
| Live penetration / Auth0 E2E | **UNVERIFIED** | Not run |

---

## Human-in-the-loop patterns

| Feature | Mechanism | Path |
| --- | --- | --- |
| Notes analysis | Staff decision on each suggestion | `notes_analysis/service.py`, `POST .../suggestions/{id}/decide` |
| Support plan draft | Review before apply | `support_plan_drafts/service.py`, `test_f37_draft_review_apply_does_not_skip_approval` |
| Report drafts | No auto-approve | `test_f313_report_drafts.py` asserts `auto_approved is False` |
| Job match explain | `require_human_gate: True` on workflow call | `job_matching/ai_client.py` |
| Safeguarding AI assist | Separate approve endpoint | `safeguarding_alerts.py` `/ai-assist`, `/ai-suggestions/{id}/approve` |
| ai-service approval service | Workflow-level gate | `apps/ai-service/app/approval/service.py` |

---

## Housing & high-impact decisions

| Rule | Implementation |
| --- | --- |
| AI must not change application status | F3.8 service records analysis only; tests `test_f38_analysis_does_not_change_application_or_waiting_list` |
| Voice assistant escalation | `voice_calling/assistant.py` escalates housing decision questions |
| Room occupancy | UI copy: never auto-approved (`RoomOccupancyDashboard.tsx`) |
| Advanced automation | Global flag off (`ADVANCED_AUTOMATION_GLOBAL_ENABLED`); separate from F3 agents |

---

## Audit & activity

| Artifact | Table / route |
| --- | --- |
| AI activity log | `ai_activity_logs` (`apps/api/app/db/models/ai_activity.py`) |
| Wrong-answer feedback | `ai_wrong_answer_feedback` |
| General audit | `record_event` on AI completions (e.g. housing analysis audit events) |
| API | `/api/v1/ai-activity` |

---

## Auth & secrets

| Check | Result |
| --- | --- |
| Hardcoded LLM keys in `apps/` | **None found** (grep) |
| Mock provider explicit opt-in | `MockLlmProvider` — `LLM_PROVIDER=mock` only |
| Internal budget endpoints | Bearer `AI_SERVICE_TOKEN` required |

---

## Gaps / UNVERIFIED

- Postgres RBAC/isolation tests for all six agents (environment)
- Live ai-service + API with real tokens and browser dashboards
- OpenAI-compatible provider with production keys (not exercised)