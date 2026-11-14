# PROMPT 3 — Tenant management (M02) audit

**Date:** 2026-11-14  
**Branch:** `develop` (implementation pass after `4656895`)  
**Scope:** M02.1–M02.4

---

## Module summary

| Metric | Value |
| --- | ---: |
| Features | 4 |
| **PASS** (verified) | **4** |
| **Verified completion** | **100%** |

---

## Design choice (M02.2)

**Source of truth:** `tenants.needs_goals` (F1.6 column) exposed on **`GET/PATCH /tenant/me`** for the linked tenant row only. Staff-internal `notes` and `consent_notes` remain omitted. Structured F2.9 rows in `tenant_needs_goals` stay staff-managed via timeline APIs — not duplicated.

---

## Feature matrix

| ID | Feature | Status | Web | Mobile | API | Tables | Tests | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M02.1 | Profile / contact | **PASS** | Caseload detail | `tenants.ts`, `HmoreAccount` | `tenant_me.py` | `tenants` | `test_f41_tenant_mobile` | **PASS** |
| M02.2 | Needs & goals | **PASS** | Caseload shows `needs_goals` | Account + Support tab read | `TenantSelfOut.needs_goals`, patch allow-list | `tenants.needs_goals` | `test_tenant_can_patch_own_name_and_phone_only`, `test_tenant_own_profile_needs_goals_isolated_per_login` | **PASS** |
| M02.3 | Timeline / follow-ups | **PASS** | `TenantTimelinePanel` | `timeline.ts` | `tenant_timeline.py` | timeline tables | `test_f29_*` | **PASS** |
| M02.4 | Own-record access | **PASS** | N/A | `/tenant/me` scope | `profile.require_own_tenant` | `tenants` | `test_f41_*` isolation | **PASS** |

---

## Files changed (this pass)

| Path | Change |
| --- | --- |
| `apps/api/app/tenant_portal/schemas.py` | `needs_goals` on out + patch |
| `apps/api/app/tenant_portal/profile.py` | Self patch field allow-list |
| `apps/api/app/support/service.py` | Caseload detail includes `needs_goals` |
| `apps/web/.../caseload/[tenantId]/page.tsx` | Display needs & goals |
| `room-ready/lib/hmore/types.ts`, `services/tenants.ts` | Type + patch whitelist |
| `room-ready/components/tenant/HmoreAccount.tsx`, `TenantSupport.tsx` | UI |

---

## Journey A (automated)

| Step | Test | Status |
| --- | --- | --- |
| Read/patch own needs_goals | `test_f41_tenant_mobile` (postgres) | **PASS** |
| Tenant A vs B isolation | `test_tenant_own_profile_needs_goals_isolated_per_login` | **PASS** |

Auth0 live profile: **UNVERIFIED**.