# RBAC Testing (F1.4)

## Distinction: mocked vs live identity

| Kind | What it covers | Files |
| --- | --- | --- |
| Mocked / unit | Roles, matrix, service helpers, API deps with overrides | `tests/test_rbac_registry.py`, `tests/test_rbac_authorization.py` |
| PostgreSQL | Assignment rules, `authorization_version`, migrations | `tests/test_rbac_assignment.py`, `tests/test_db_schema.py` |
| Live Auth0 | Real login/MFA | Not required for F1.4 CI; follow `AUTHENTICATION_TESTING.md` |

Never report a live Auth0 test as passed unless a real tenant was used.

## Commands

From `apps/api` with the project venv activated:

```text
# Registry + authorization (no Postgres required for most)
python -m pytest tests/test_rbac_registry.py tests/test_rbac_authorization.py tests/test_auth_tokens.py tests/test_health.py -q

# With DATABASE_URL / TEST_DATABASE_URL pointing at pgvector
python -m pytest tests/test_rbac_assignment.py tests/test_db_schema.py tests/test_auth_identity.py -q
```

Web (no Jest suite yet):

```text
cd apps/web
npm run typecheck
npm run lint
```

## Coverage map

| Requirement | Test |
| --- | --- |
| Exactly six roles | `test_exactly_six_approved_roles` |
| Reject unknown roles | `test_unknown_role_rejected` |
| Matrix allow/deny | `test_explicit_allows`, `test_deny_by_default_unmapped_permission` |
| No wildcards | `test_no_wildcard_permission_identifier` |
| 401 unauthenticated | `test_api_unauthenticated_returns_401` |
| 403 unauthorized | `test_api_unauthorized_returns_403` |
| 200 authorized | `test_api_authorized_returns_ok` |
| Client role ignored | `test_client_supplied_role_header_ignored_without_membership` |
| Privilege escalation | landlord/contractor/support/org-admin tests in authorization + assignment |
| Session version | `test_session_policy_exposes_authorization_version` |
| Assignment + version bump | `test_super_admin_assign_bumps_authorization_version` |
| Migration head | `test_migration_history_has_single_head` |
| F1.3 regression | existing `test_auth_*` + `/api/v1/auth/me` still present |

## Manual probes

With a Bearer token:

```text
GET /api/v1/rbac/me
GET /api/v1/rbac/gates/organisations.manage
GET /api/v1/rbac/session
```

Expect 403 for roles without the gate permission.
