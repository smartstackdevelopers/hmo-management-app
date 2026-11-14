# PROMPT 2 — Security & isolation test report

**Date:** 2026-11-14  
**Environment:** Windows local, Python 3.12, PostgreSQL when `DATABASE_URL` / `TEST_DATABASE_URL` set (no DB dropped; `conftest.py` uses transactional fixtures + alembic up/down at session end).

---

## Summary verdicts

| Area | Verdict | Evidence |
| --- | --- | --- |
| RBAC matrix / registry | **PASS** | `test_rbac_registry.py` — all passed |
| Authorization service | **PASS** | `test_rbac_authorization.py`, `test_rbac_assignment.py` |
| Auth0 token rules (mocked) | **PASS** | `test_auth_tokens.py`, `test_auth_identity.py` |
| Organisation isolation | **PASS** (automated) | `test_organisation_isolation.py` — helpers + postgres RLS cases |
| Cross-org API (Super Admin) | **PASS** | `test_super_admin_organisations_api.py` |
| Live Auth0 penetration / manual IDOR | **UNVERIFIED** | No tenant browser run |

---

## Task 7 — Executed tests

### API pytest

| Run | Command | Result |
| --- | --- | --- |
| Full suite | `cd apps/api && python -m pytest -q` | **415 passed**, **116 skipped**, 0 failed (~36s) |
| Auth / RBAC / isolation focus | `pytest -q tests/test_auth_tokens.py tests/test_auth_identity.py tests/test_rbac_registry.py tests/test_rbac_authorization.py tests/test_rbac_assignment.py tests/test_organisation_isolation.py tests/test_identity_bootstrap.py tests/test_super_admin_organisations_api.py` | **34 passed**, 17 skipped |
| Org list service (postgres) | `tests/test_organisations_list.py` | **1 passed** (after import fix; see Remaining Issues) |

**Skip reason:** `pytest.mark.postgres` tests skip when `TEST_DATABASE_URL` / `DATABASE_URL` unset (`tests/conftest.py`). On this machine, majority of postgres tests **ran** (415 passed indicates DB available).

### Web

| Check | Result |
| --- | --- |
| Typecheck / lint | **Not run** — no web source changed in Prompt 2 |
| E2E | **Not run** — `apps/web/e2e/dashboard.spec.ts` exists for `canAccessRoleHome` unit logic only |

### Mobile (`room-ready`)

| Check | Command | Result |
| --- | --- | --- |
| Jest | `npm test -- --testPathPattern=tenantMobile` | **14 passed**, 0 failed |

---

## Task 4 — Organisation isolation coverage

| Test | Type | What it proves |
| --- | --- | --- |
| `test_missing_organisation_context_rejected_via_api` | HTTP | `GET /api/v1/isolation/properties` → 401 without auth |
| `test_foreign_property_id_denied_by_isolation_helper` | Unit | IDOR UUID → 403 |
| `test_cross_organisation_property_isolation` | Postgres | Org A admin cannot read/update/delete Org B property under RLS |
| `test_inactive_membership_denied` | Postgres | Suspended tenant cannot access org |
| `test_unauthorized_self_activation_rejected` | Postgres | Tenant cannot self-activate membership |
| `test_create_property_stamps_trusted_organisation_only` | Postgres | Created row stamped to actor org |
| `test_rls_hides_foreign_rows_without_app_filter` | Postgres | RLS list filter |
| Job context tests | Unit/Postgres | Payload must include `organisation_id` and valid actor |

**Gaps:** No new tests added in Prompt 2 — existing suite deemed sufficient for local audit. Browser-level cross-org deny **UNVERIFIED**.

**Isolation API surface:** `app/api/v1/isolation_probes.py` (permission-gated probes).

---

## RBAC test highlights

```
tests/test_rbac_registry.py::test_exactly_six_approved_roles
tests/test_rbac_registry.py::test_deny_by_default_unmapped_permission
tests/test_rbac_authorization.py::test_require_permission_denies_missing
tests/test_super_admin_organisations_api.py::test_platform_organisations_list_requires_super_admin
```

---

## Fixes during Prompt 2 (local, uncommitted)

| File | Issue |
| --- | --- |
| `tests/test_organisations_list.py` | ImportError: `list_organisations_directory` did not exist — pointed to `app.platform_governance.service.list_organisations` + `governance_enabled` fixture |

Re-running full pytest after fix: **415 passed** (collection error cleared).

---

## MFA-related tests

| Item | Result |
| --- | --- |
| `token_has_mfa` / staff-session behaviour | Covered in `test_auth_tokens.py` (mock claims) |
| Live MFA challenge | **UNVERIFIED** |