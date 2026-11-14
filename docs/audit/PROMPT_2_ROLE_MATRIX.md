# PROMPT 2 — Six-role matrix and enforcement

**Date:** 2026-11-14 (follow-up)  
**Branch:** `develop` @ `95bed7a`  
**Verdict (six roles only):** **PASS**  
**Verdict (web route homes):** **PARTIAL**  
**Verdict (live Auth0 role claims):** **UNVERIFIED**

---

## Task 2 — Exactly six roles

| Check | Evidence | Verdict |
| --- | --- | --- |
| DB enum | `apps/api/app/db/models/enums.py` — `HMoreRole` (6 values) | **PASS** |
| Registry | `apps/api/app/rbac/roles.py` — `ROLE_DEFINITIONS`, `APPROVED_ROLE_COUNT = 6` | **PASS** |
| Startup guard | `roles.py` — `assert_exactly_six_roles()` at import | **PASS** |
| Tests | `tests/test_rbac_registry.py::test_exactly_six_approved_roles` | **PASS** |
| Web | `apps/web/src/lib/rbac.ts` — `APPROVED_ROLES` length 6 | **PASS** |
| Bootstrap CLI | `apps/api/scripts/bootstrap_identity.py` — `list-roles` | **PASS** |

| Code | Display name | Platform-scoped |
| --- | --- | --- |
| `super_admin` | Super Admin | Yes |
| `organisation_admin` | Organisation Admin | No |
| `landlord` | Landlord | No |
| `tenant` | Tenant | No |
| `support_worker` | Support Worker | No |
| `maintenance_contractor` | Maintenance & Contractors | No |

Forbidden legacy values explicitly tested: `council_officer`, `housing_manager`, etc. — `test_no_removed_core_roles`.

---

## Task 3 — RBAC enforcement map

### Layers

| Layer | File | Role |
| --- | --- | --- |
| Permissions | `app/rbac/permissions.py` | `Permission` enum + `PERMISSION_CATALOG` |
| Matrix | `app/rbac/matrix.py` | `ROLE_PERMISSIONS` — deny unlisted |
| Context | `app/rbac/context.py` | `AuthorizationContext.has_permission()` |
| Service | `app/rbac/service.py` | `require_permission`, `assert_landlord_property_access`, `assert_same_user`, … |
| HTTP deps | `app/rbac/deps.py` | `require_perm(...)`, `get_authorization_context` |
| Assignment | `app/rbac/assignment.py` | `assign_membership` rules |
| Tenancy | `app/tenancy/membership_service.py` | Org membership mutations |
| Isolation | `app/tenancy/isolation.py` | Org-scoped CRUD helpers + RLS |

### RBAC HTTP API (`/api/v1/rbac`)

| Method | Path | Permission / gate |
| --- | --- | --- |
| GET | `/rbac/roles` | Authenticated + membership |
| GET | `/rbac/permissions` | Authenticated + membership |
| GET | `/rbac/matrix` | `audit_logs.read` |
| GET | `/rbac/me` | Authenticated + active membership |
| GET | `/rbac/session` | Session policy |
| POST | `/rbac/memberships` | Assignment rules in service |
| GET | `/rbac/gates/organisations.manage` | Permission probe |
| GET | `/rbac/gates/audit_logs.read` | Permission probe |
| GET | `/rbac/gates/properties.manage` | Permission probe |
| POST | `/rbac/gates/property-access` | Landlord scope assert |
| POST | `/rbac/gates/work-order-access` | Contractor scope assert |
| POST | `/rbac/gates/support-access` | Support worker caseload assert |
| POST | `/rbac/gates/own-profile` | Tenant self assert |

### Role → enforcement examples

| Role | Matrix source | Scoped asserts | Example tests |
| --- | --- | --- | --- |
| **Super Admin** | Full platform set in `matrix.py` | `get_platform_context` on org create | `test_super_admin_organisations_api.py` |
| **Org Admin** | Org admin frozenset | Org context on CRUD | `test_organisation_isolation.py` |
| **Landlord** | `PROPERTIES_*`, repairs | `assert_landlord_property_access` | `test_rbac_authorization.py` |
| **Tenant** | Own repairs, limited reads | `assert_same_user` | `test_tenant_own_profile_only` |
| **Support Worker** | Caseload, plans, visits | `assert_assigned_support_caseload` | `test_rbac_authorization.py` |
| **Contractor** | Work orders assigned | `assert_assigned_work_order` | matrix + maintenance tests |

Representative routers using `require_permission` / `require_perm`: `properties.py`, `tenants.py`, `files.py`, `audit.py`, `emergency_access.py`, `platform_governance.py`, `organisations.py`, `isolation_probes.py`.

### UI (non-authoritative)

| File | Behaviour |
| --- | --- |
| `apps/web/src/lib/rbac.ts` | `can()`, `APPROVED_ROLES` |
| `apps/web/src/lib/navigation.ts` | Nav filtered by permissions from API |
| `apps/web/src/lib/session.ts` | Server-side role home guard |

---

## Web dashboard route protection

| File | `requireDashboardRole` |
| --- | --- |
| `src/app/dashboard/super-admin/page.tsx` | `super_admin` |
| `src/app/dashboard/super-admin/organisations/page.tsx` | `super_admin` |
| `src/app/dashboard/organisation-admin/page.tsx` | `organisation_admin` |
| `src/app/dashboard/support-worker/page.tsx` | `support_worker` |
| `src/app/dashboard/landlord/*` | **No** `requireDashboardRole` in repo grep — **PARTIAL** |

Role homes: `apps/web/src/lib/dashboardAccess.ts` — `ROLE_DASHBOARD_HOMES` (4 web roles); tenant/contractor → `/account`.

---

## Task 6 — Acceptance checklist (E2E)

| ID | Role | Client | Status |
| --- | --- | --- | --- |
| R1 | super_admin | Web | **UNVERIFIED** |
| R2 | organisation_admin | Web | **UNVERIFIED** |
| R3 | landlord | Web | **UNVERIFIED** |
| R4 | support_worker | Mobile | **UNVERIFIED** |
| R5 | tenant | Mobile | **UNVERIFIED** |
| R6 | maintenance_contractor | Mobile | **UNVERIFIED** |

Checklist file: `docs/development/ROLE_ACCEPTANCE_CHECKLIST.csv`. Manual procedure: `PROMPT_2_REMAINING_ISSUES.md`.