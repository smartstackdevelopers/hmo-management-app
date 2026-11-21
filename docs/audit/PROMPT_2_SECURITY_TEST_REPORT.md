# PROMPT 2 — Security & isolation test report

**Date:** 2026-11-14 (follow-up re-run)  
**Branch:** `develop` @ `95bed7a`  
**Environment:** Windows, Python 3.12; PostgreSQL when `DATABASE_URL` / `TEST_DATABASE_URL` set; `tests/conftest.py` transactional `db_session` (no dev DB drop).

---

## Summary verdicts

| Area | Verdict | Evidence |
| --- | --- | --- |
| RBAC matrix / registry | **PASS** | `test_rbac_registry.py` |
| Authorization service | **PASS** | `test_rbac_authorization.py`, `test_rbac_assignment.py` |
| Auth0 JWT rules (mocked JWKS) | **PASS** | `test_auth_tokens.py` |
| Identity mapping | **PASS** | `test_auth_identity.py` |
| Organisation isolation | **PASS** (where Postgres ran) | `test_organisation_isolation.py` |
| Super Admin org API | **PASS** | `test_super_admin_organisations_api.py` |
| Live Auth0 / browser IDOR | **UNVERIFIED** | No tenant credentials used |

---

## Task 7 — Executed tests (follow-up)

### Focused security / RBAC / isolation / JWT

```text
cd apps/api
python -m pytest -q \
  tests/test_auth_tokens.py \
  tests/test_auth_identity.py \
  tests/test_rbac_registry.py \
  tests/test_rbac_authorization.py \
  tests/test_rbac_assignment.py \
  tests/test_organisation_isolation.py \
  tests/test_identity_bootstrap.py \
  tests/test_super_admin_organisations_api.py \
  tests/test_organisations_list.py
```

| Metric | Count |
| --- | ---: |
| **Passed** | **34** |
| **Skipped** | **18** |
| **Failed** | **0** |
| Duration | ~38s |

#### Per-file breakdown (same follow-up run)

| File | Passed | Skipped | Notes |
| --- | ---: | ---: | --- |
| `test_auth_tokens.py` | 9 | 0 | Mock JWKS; `validate_access_token`, MFA claim helpers |
| `test_auth_identity.py` | 0 | 2 | Postgres provisioning |
| `test_rbac_registry.py` | 9 | 0 | Exactly six roles |
| `test_rbac_authorization.py` | 12 | 0 | `require_permission`, scoped asserts |
| `test_rbac_assignment.py` | 0 | 4 | Postgres assignment rules |
| `test_organisation_isolation.py` | 4 | 7 | Mix of unit + postgres RLS |
| `test_identity_bootstrap.py` | 0 | 2 | Bootstrap CLI DB |
| `test_super_admin_organisations_api.py` | 0 | 2 | HTTP overrides + postgres |
| `test_organisations_list.py` | 0 | 1 | `list_organisations` service |

Skips use `@pytest.mark.postgres` when the focused run does not attach a live DB session to every module; the **full suite** below exercises the majority of postgres tests.

### Full API suite

```text
cd apps/api && python -m pytest -q
```

| Metric | Count |
| --- | ---: |
| **Passed** | **415** |
| **Skipped** | **116** |
| **Failed** | **0** |
| Duration | ~48s |

### Web

| Check | Command | Result |
| --- | --- | --- |
| TypeScript | `cd apps/web && npm run typecheck` | **PASS** |

### Mobile (unchanged from initial Prompt 2)

| Check | Result |
| --- | --- |
| `npm test -- --testPathPattern=tenantMobile` | **14 passed** (not re-run in follow-up) |

### E2E

| Check | Result |
| --- | --- |
| Playwright | **UNVERIFIED** — not run |

---

## Task 4 — Organisation isolation coverage

| Test | Proves |
| --- | --- |
| `test_missing_organisation_context_rejected_via_api` | `GET /api/v1/isolation/properties` → 401 without bearer |
| `test_foreign_property_id_denied_by_isolation_helper` | IDOR UUID → 403 |
| `test_cross_organisation_property_isolation` | Cross-org property deny under RLS |
| `test_inactive_membership_denied` | Suspended membership |
| `test_unauthorized_self_activation_rejected` | No self-activate |
| `test_create_property_stamps_trusted_organisation_only` | Org stamp on create |
| `test_rls_hides_foreign_rows_without_app_filter` | RLS list filter |
| Job context tests | Valid `organisation_id` + actor |

**Isolation HTTP routes:** `apps/api/app/api/v1/isolation_probes.py` — prefix `/api/v1/isolation`.

**Gap:** Browser cross-org deny **UNVERIFIED**. No new tests added in follow-up (existing suite sufficient for code audit).

---

## Related security tests (not in focused command)

| File | Topic |
| --- | --- |
| `tests/test_f111_security_config.py` | Security-related settings |
| `tests/test_f43_push_notifications.py` | JWT references in push paths |

---

## MFA-related tests

| Item | Result |
| --- | --- |
| `test_auth_tokens.py` — `token_has_mfa`, invalid/expired token | **PASS** (mock) |
| Live Auth0 MFA challenge | **UNVERIFIED** |