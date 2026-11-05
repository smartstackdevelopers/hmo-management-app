# Organisation Isolation Testing (F1.5)

## Mocked vs PostgreSQL

| Kind | Files | Needs Postgres |
| --- | --- | --- |
| HTTP 401 / IDOR-style API probes | `tests/test_organisation_isolation.py` (non-postgres) | No |
| Cross-org isolation, RLS, membership, jobs | same file (`@pytest.mark.postgres`) | Yes |
| Schema / migration head | `tests/test_db_schema.py` | Yes |
| RBAC regression | `tests/test_rbac_*.py` | Mixed |

## Commands

```text
cd apps/api
python -m pytest tests/test_organisation_isolation.py tests/test_rbac_registry.py tests/test_rbac_authorization.py tests/test_health.py -q

# With DATABASE_URL pointing at pgvector:
python -m pytest tests/test_organisation_isolation.py tests/test_db_schema.py -q
```

## Cross-organisation checklist covered

- Org A cannot list/read/update/delete Org B properties
- Org B cannot access Org A properties
- Inactive membership denied
- Unauthorized self-activation rejected
- Job actor without membership rejected
- RLS list visibility limited to current `app.organisation_id`

## Manual probes

With Bearer token and `X-Organisation-Id` of an active membership:

```text
GET  /api/v1/organisations/me/context
GET  /api/v1/isolation/properties
POST /api/v1/isolation/properties
GET  /api/v1/isolation/properties/{foreign-uuid}   # expect 403
```
