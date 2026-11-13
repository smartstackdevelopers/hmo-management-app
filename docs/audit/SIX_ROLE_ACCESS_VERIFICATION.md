# Six-role access verification

**Core roles (only):** `HMoreRole` enum — Super Admin, Organisation Admin, Landlord, Tenant, Support Worker, Maintenance & Contractors.

**Evidence:** `apps/api/tests/test_rbac_registry.py::test_exactly_six_approved_roles`

## Verification method

| Check | Evidence |
| --- | --- |
| Role permission matrix | `apps/api/app/rbac/matrix.py` + registry tests |
| Assignment rules | `test_rbac_assignment.py` |
| Authorization deny | `test_rbac_authorization.py` |
| Organisation isolation | `test_f15_*`, postgres tests in CI |
| Landlord property scope | `test_f61_landlord_enterprise.py` (post Phase 6 fix) |
| Tenant self-access | `test_f29_tenant_timeline.py`, tenant routes |
| Contractor maintenance only | `test_f28_maintenance.py` matrix |
| Super Admin cross-org | super admin routes with audit |
| Finance denied to tenant | `test_f66_finance_module.py` |
| F6.1 denied to support worker | `test_f61_landlord_enterprise.py` |

## Council portal

Council officers use **add-on** tables — **not** a seventh `HMoreRole`. See `test_f67_council_portal.py`.

## Sensitive data

- File download permissions: `test_f18_storage.py::test_files_permissions_matrix`
- AI routes require service token + org flags: AI pytest suite
- Occupancy ingest: 403 until privacy gate — `test_f65_room_occupancy.py`

## Document permissions

Managed documents module — org-scoped keys; retention and access request APIs in F2.11 tests.

## Gaps

- Exhaustive UI per-role click-through for every nav item: **PARTIAL** (sidebar filtered in `navigation.ts` — manual spot checks recommended)
- Production Auth0 role claims vs matrix: **PENDING APPROVAL** staging smoke
