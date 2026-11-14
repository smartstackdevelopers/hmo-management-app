# PROMPT 2 — Six-role matrix and enforcement

**Date:** 2026-11-14  
**Verdict (six roles only):** **PASS**  
**Verdict (web route homes):** **PARTIAL**  
**Verdict (live Auth0 role claims):** **UNVERIFIED**

---

## Task 2 — Exactly six roles

| Check | Evidence | Verdict |
| --- | --- | --- |
| DB enum | `apps/api/app/db/models/enums.py` — `HMoreRole` (6 values) | **PASS** |
| Registry | `apps/api/app/rbac/roles.py` — `ROLE_DEFINITIONS`, `APPROVED_ROLE_COUNT = 6`, `assert_exactly_six_roles()` | **PASS** |
| Forbidden legacy roles | `tests/test_rbac_registry.py::test_no_removed_core_roles` | **PASS** |
| Web approved list | `apps/web/src/lib/rbac.ts` — `APPROVED_ROLES` (6 strings) | **PASS** |
| Council / add-ons | Not seventh core role (`docs/audit/SIX_ROLE_ACCESS_VERIFICATION.md`) | **PASS** |

### Role codes and display names

| Code | Display name | Platform-scoped |
| --- | --- | --- |
| `super_admin` | Super Admin | Yes |
| `organisation_admin` | Organisation Admin | No |
| `landlord` | Landlord | No |
| `tenant` | Tenant | No |
| `support_worker` | Support Worker | No |
| `maintenance_contractor` | Maintenance & Contractors | No |

---

## Task 3 — RBAC (backend enforcement, not UI-only)

| Layer | Mechanism | Key paths |
| --- | --- | --- |
| Permission catalog | `app/rbac/permissions.py` | Stable permission IDs |
| Matrix | `app/rbac/matrix.py` — `ROLE_PERMISSIONS` | Deny-by-default |
| Service | `app/rbac/service.py` — `require_permission`, scoped asserts (landlord property, caseload, own user) | Used across routers |
| HTTP deps | `app/rbac/deps.py` — `require_perm(...)`, `get_authorization_context` | Membership + optional device session |
| Audit on deny | `require_perm` records `AUTH_ACCESS_DENIED` | `app/rbac/deps.py` |

**API usage:** Widespread `require_permission` / `require_perm` on v1 routers (properties, tenants, files, rbac, audit, isolation probes, AI usage, etc.). UI `can()` in `apps/web` is explicitly non-authoritative.

### Permission summary by role (high level)

| Role | Representative backend capabilities |
| --- | --- |
| **Super Admin** | Organisations create/manage, platform settings, role assignments, audit read, cross-org governance (`ORGANISATIONS_*`, `PLATFORM_*`, full finance/add-ons set in matrix) |
| **Org Admin** | Org users/workflows, compliance, audit/reports, occupancy, communications, housing ops — not platform org creation |
| **Landlord** | Own properties/rooms/vacancies, tenancies, inspections, repairs on own stock (`PROPERTIES_*`, landlord-scoped asserts) |
| **Tenant** | Own profile/documents, own repairs/complaints, limited reads — denied admin/audit/finance (`REPAIRS_CREATE_OWN`, self-user asserts) |
| **Support Worker** | Assigned caseload, support plans/notes, visits/tasks, incidents — denied unrelated tenants (`SUPPORT_*`, assignment asserts) |
| **Maintenance contractor** | Assigned work orders, status/photo updates — denied role assignment and broad admin (`WORK_ORDERS_*`) |

Detailed per-permission mapping: `apps/api/app/rbac/matrix.py` + `tests/test_rbac_registry.py`.

### Scoped enforcement examples (beyond matrix)

| Scenario | Test / code |
| --- | --- |
| Tenant ≠ other user | `test_rbac_authorization.py::test_tenant_own_profile_only` |
| Landlord ≠ foreign property | `test_rbac_authorization.py::test_landlord_cannot_access_unrelated_property` |
| Super Admin org API | `test_super_admin_organisations_api.py` (403 for tenant on platform org list) |

---

## Web dashboard route protection

| Mechanism | Path |
| --- | --- |
| Role home map | `apps/web/src/lib/dashboardAccess.ts` — four F19 web homes + tenant/contractor → `/account` |
| Server guard | `requireDashboardRole` in `src/lib/session.ts` |
| Pages using guard | `dashboard/super-admin/*`, `organisation-admin`, `landlord`, `support-worker` (grep `requireDashboardRole`) |

| Role | Web home | Guarded page |
| --- | --- | --- |
| super_admin | `/dashboard/super-admin` | **PASS** |
| organisation_admin | `/dashboard/organisation-admin` | **PASS** |
| landlord | `/dashboard/landlord` | **PARTIAL** (home guarded; deep routes rely on API + nav) |
| support_worker | `/dashboard/support-worker` | **PASS** |
| tenant | Mobile primary (`ROLE_ACCEPTANCE_CHECKLIST.csv` R5) | **PARTIAL** on web |
| maintenance_contractor | Mobile primary (R6) | **PARTIAL** on web |

**Verdict:** Six roles in data model **PASS**; exhaustive per-nav-item web deny **PARTIAL** (`docs/audit/SIX_ROLE_ACCESS_VERIFICATION.md` agrees).

---

## Task 6 cross-reference (role E2E)

| ID | Role | Client | Checklist status |
| --- | --- | --- | --- |
| R1 | super_admin | Web | **UNVERIFIED** |
| R2 | organisation_admin | Web | **UNVERIFIED** |
| R3 | landlord | Web | **UNVERIFIED** |
| R4 | support_worker | Mobile | **UNVERIFIED** |
| R5 | tenant | Mobile | **UNVERIFIED** |
| R6 | maintenance_contractor | Mobile | **UNVERIFIED** |