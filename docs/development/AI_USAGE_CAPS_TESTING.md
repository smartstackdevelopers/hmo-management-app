# F3.3 testing guide

## Unit (no database)

```bash
cd apps/api
pytest tests/test_f33_ai_usage_cost_unit.py -q
pytest tests/test_f33_ai_usage_caps.py::test_f33_rbac_matrix_roles -q
```

Covers: verified pricing maths, missing pricing, cache-hit policy, period helpers,
RBAC matrix.

## PostgreSQL integration

Requires `TEST_DATABASE_URL` or `DATABASE_URL` (PostgreSQL + migrations).

```bash
cd apps/api
pytest tests/test_f33_ai_usage_caps.py -m postgres -q
```

Covers: budget upsert, hard-cap rejection (402), idempotent request_id,
failure release, RLS cross-org denial, dashboard aggregates, concurrent
reservation serialisation.

## AI service

```bash
cd apps/ai-service
pytest tests/test_budget_client.py -q
```

Budget client tests use httpx mocks — not real provider billing.

## Distinctions

| Kind | Claim |
| --- | --- |
| Unit / mocked httpx | Deterministic logic only |
| Real PostgreSQL (`-m postgres`) | Cap enforcement + RLS |
| Real Redis / Celery / LLM | Not required for F3.3 acceptance of caps |

Never report skipped postgres tests as passed. Never report mocked costs as
provider billing.
