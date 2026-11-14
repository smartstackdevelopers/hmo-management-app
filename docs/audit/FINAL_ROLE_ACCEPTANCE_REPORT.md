# FINAL — Six role acceptance (Prompt 7)

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Git | `f3097b2` |
| Checklist ref | `docs/development/ROLE_ACCEPTANCE_CHECKLIST.csv` |

## Automated evidence

| Role | Primary tests / code |
| --- | --- |
| `super_admin` | `test_rbac_registry.py`, platform governance routes |
| `organisation_admin` | RBAC matrix, `test_f213_org_workflows.py` (when DB up) |
| `landlord` | `test_f61_landlord_enterprise.py` (skipped if no DB) |
| `tenant` | `test_f41_tenant_mobile.py` — **extended in Prompt 3** |
| `support_worker` | `test_f21_support_caseloads.py`, `test_f42_staff_mobile_unit.py` |
| `maintenance_contractor` | RBAC + `test_f28_maintenance.py` |

`scripts/bootstrap-identity.ps1 list-roles` — **6 roles** (Prompt 1 evidence; not re-run in Prompt 7).

## Local login verification

| Role | Browser / device verified? |
| --- | --- |
| All six | **NO** |

Auth0 env files were **not read** (gitignored). `meeting-demo.local.env` was **not read**.

## Module expectations per role (plan §4)

| Role | Mandatory modules for LOCAL 100% | Prompt 7 status |
| --- | --- | --- |
| super_admin | M01, M10.1, audit | **PARTIAL** |
| organisation_admin | M10.2–M10.4, M13 | **PARTIAL** |
| landlord | M03, M08, M13 | **PARTIAL** |
| support_worker | M02, M04, M05 | **PARTIAL** (tests improved) |
| tenant | M02, M06–M09, M08.1 | **PARTIAL** |
| maintenance_contractor | M08.3 | **PARTIAL** |

## Verdict

**Six-role LOCAL acceptance: NOT ACHIEVED** (0/6 roles proven on Auth0 stack this session).