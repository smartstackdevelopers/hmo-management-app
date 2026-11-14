# PROMPT 3 — Support plans (M05) audit

**Date:** 2026-11-14  
**Branch:** `develop` @ `95bed7a`  
**Scope:** M05.1 goals/milestones, M05.2 reviews/export (includes overlap with M02.2 structured goals)

---

## Module summary

| Metric | Value |
| --- | ---: |
| Features audited | 2 |
| **PASS** (API + executed tests) | 2 |
| **PARTIAL** (browser-only) | 0 |
| **Verified completion** | **100%** (API); **PARTIAL** for web PDF download smoke |

---

## Feature matrix

| ID | Feature | Status | Web | Mobile | API | DB tables | Tests (executed) | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **M05.1** | Goals & milestones | **PASS** | `/dashboard/support-plans` (dashboard counts); `/dashboard/support-plans/tenant?tenantId=`; draft panel | `supportPlans.ts` → `/tenant/support-plans` (read-only tenant) | `apps/api/app/api/v1/support_plans.py`; `support_plans/service.py` | `tenant_support_plans`, `support_plan_goals`, `support_plan_milestones`, history tables | `test_f210_support_plans.py::test_f210_plan_lifecycle_and_isolation` | **PASS** |
| **M05.2** | Reviews & export | **PASS** (API) | Dashboard aggregates via `fetchSupportPlansDashboard`; export download via API routes (no browser run) | Tenant read-only plan detail | `POST .../exports`, PDF via `app/evidence/pdf.py` | `support_plan_reviews`, `support_plan_progress_exports` | Same lifecycle test (`create_progress_export`, `test_pdf_generation_unit`) | **PASS** (automated); web click-through **UNVERIFIED** |

---

## Lifecycle covered in `test_f210_plan_lifecycle_and_isolation`

- Plan create → activate transitions  
- Goals, milestones, reviews  
- Milestone complete → goal achieve  
- Progress export (non-internal) with file artefact  
- Tenant read strips `internal_notes`  
- Landlord property-scoped read  
- Plan revise / supersede  
- Cross-organisation denial within test fixture  

---

## AI support-plan drafts (related, not M05 core)

| Component | Status | Test |
| --- | --- | --- |
| Draft compose / cap | Automated | `test_f37_support_plan_drafts.py` (in M02–M05 subset: passed) |
| Web `SupportPlanDraftPanel` | Wired to API when permitted | Not browser-verified |

---

## Frontend wiring

| File | Behaviour |
| --- | --- |
| `apps/web/src/lib/supportPlansApi.ts` | Server-side fetch to HMore API with org + role headers |
| `apps/web/src/app/dashboard/support-plans/page.tsx` | Real dashboard metrics; error/empty states |
| `apps/web/src/app/dashboard/support-plans/tenant/page.tsx` | Tenant-scoped list; empty when none |

No stub counters or hardcoded plan rows.

---

## Journey C — Structured support plan (automated)

| Step | Evidence | Status |
| --- | --- | --- |
| Staff creates plan with goals/milestones | `test_f210_plan_lifecycle_and_isolation` | **PASS** |
| Review + export | Export row + PDF builder unit | **PASS** |
| Tenant read-only view | Service assertion in same test | **PASS** |
| Cross-org | Isolation assertions in F2.10 test | **PASS** |

---

## Remaining issues (M05)

1. Download export PDF from web UI with Auth0 session — **UNVERIFIED** (API proven).
2. Mobile does not implement staff-side plan management (tenant read-only only) — acceptable per role matrix; web is primary staff surface.