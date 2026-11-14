# PROMPT 3 — Tenant management (M02) audit

**Date:** 2026-11-14  
**Branch:** `develop` @ `95bed7a` (Prompt 2)  
**Scope:** M02.1–M02.4 — profile/contact, needs & goals, timeline/follow-ups, tenant own-record access

---

## Module summary

| Metric | Value |
| --- | ---: |
| Features audited | 4 |
| **PASS** (verified by executed tests) | 3 |
| **PARTIAL** | 1 |
| **Verified completion** | **75%** |

---

## Feature matrix

| ID | Feature | Status | Web | Mobile | API / service | DB tables | Tests (executed) | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **M02.1** | Tenant profile / contact | **PASS** | `apps/web/src/app/dashboard/caseload/[tenantId]/page.tsx` (staff view); contact fields from `fetchCaseDetail` | `room-ready/lib/hmore/services/tenants.ts` → `GET/PATCH /tenant/me`; `HmoreAccount.tsx`, `TenantHome.tsx` | `apps/api/app/api/v1/tenant_me.py`; `app/tenant_portal/profile.py` | `tenants`, `users`, `organisation_memberships` | `test_f41_tenant_mobile.py::test_tenant_can_patch_own_name_and_phone_only` | **PASS** |
| **M02.2** | Needs & goals fields | **PARTIAL** | Caseload shows profile text; structured needs via timeline/support plans (staff) | Tenant self type omits `needs_goals` (`lib/hmore/types.ts`); no tenant edit UI for staff-only fields | `tenant_timeline` needs-goals routes; `tenants.needs_goals` column; support plans goals | `tenant_needs_goals`, `tenants.needs_goals`, `support_plan_goals` | `test_f41_tenant_mobile.py::test_self_profile_schema_hides_staff_notes`; `test_f29_tenant_timeline.py` (postgres flow) | **PASS** (API staff flows); **PARTIAL** (tenant-visible needs/goals on mobile) |
| **M02.3** | Timeline / follow-ups | **PASS** | `TenantTimelinePanel` on caseload detail; `dashboard/support-plans` links | `room-ready/lib/hmore/services/timeline.ts` → `/tenants/{id}/timeline` | `apps/api/app/api/v1/tenant_timeline.py` | `tenant_meetings`, `tenant_appointments`, `tenant_follow_ups`, … | `test_f29_tenant_timeline.py::test_timeline_and_meetings_isolation` | **PASS** |
| **M02.4** | Tenant own-record access | **PASS** | N/A (tenant role uses mobile) | `GET/PATCH /tenant/me`, `GET /tenant/me/housing`, own support plans read | `tenant_me.py`; RBAC `Permission.PLANS_READ_OWN`, timeline read own | `tenants` (scoped by membership) | `test_f41_tenant_mobile.py` (patch scope, housing assignment, catalogue isolation, document upload) | **PASS** |

---

## Security & ownership (executed)

| Check | Evidence | Result |
| --- | --- | --- |
| Tenant cannot patch staff-only fields | `test_self_patch_allows_only_preferred_name_and_phone` | **PASS** |
| `needs_goals` / notes hidden from `TenantSelfOut` | `test_self_profile_schema_hides_staff_notes` | **PASS** |
| Cross-org timeline isolation | `test_timeline_and_meetings_isolation` | **PASS** |
| Housing endpoint scoped to caller | `test_housing_endpoint_returns_only_the_callers_assignment` | **PASS** |

No RBAC weakening or mock success paths were introduced in this sprint.

---

## Frontend wiring (web)

| Page | Wiring | Empty / error states |
| --- | --- | --- |
| `/dashboard/caseload/[tenantId]` | Real `fetchCaseDetail` → `/caseload/tenants/{id}` | `EmptyState`, `ErrorState`, auth redirects |
| Support-plans tenant list | Real `fetchTenantSupportPlans` | Requires `?tenantId=`; API empty list message |

**Stubs:** None found under tenant/caseload/support-plans dashboard routes (no hardcoded demo rows).

---

## Mobile vs legacy API

| Surface | Base URL | Verdict |
| --- | --- | --- |
| `room-ready/lib/hmore/config.ts` | `:8000/api/v1` default | **PASS** |
| `tenant/me`, timeline, support plans | `hmoreFetch` only | **PASS** |
| Port `3001` | Opt-in legacy only (`legacyApiConfig.ts`) | **PASS** (not default) |

---

## Remaining issues (M02)

1. **M02.2** — By design, tenants do not receive `needs_goals` on `/tenant/me`; goals live in support plans and staff timeline APIs. Add read-only tenant-safe summary if product requires mobile display.
2. **Auth0 E2E** — Live tenant login and profile edit on device: **UNVERIFIED** (no session in this audit).

---

## Journey A — Tenant self-service (automated)

| Step | Test | Status |
| --- | --- | --- |
| Patch own name/phone | `test_tenant_can_patch_own_name_and_phone_only` | **PASS** |
| Read assigned housing only | `test_housing_endpoint_returns_only_the_callers_assignment` | **PASS** |
| Catalogue / org isolation | `test_catalogues_hide_unpublished_and_other_organisations` | **PASS** |

Auth0 browser journey: **UNVERIFIED**.