# F1.6 Testing

## Suites

| File | Kind |
| --- | --- |
| `tests/test_f16_records.py` | Matrix unit + 401 + Postgres isolation/CRUD |
| `tests/test_rbac_*` | Regression |
| `tests/test_organisation_isolation.py` | F1.5 regression |
| `tests/test_db_schema.py` | Migration head `20261105_1800_f16` |

## Commands

```text
cd apps/api
pytest tests/test_f16_records.py tests/test_rbac_registry.py tests/test_health.py -q
# With DATABASE_URL:
pytest tests/test_f16_records.py tests/test_db_schema.py -q
```

## Audit note

CRUD writes `audit_events` via the F1.7 central service (`app.audit.service`). See [AUDIT_TESTING.md](./AUDIT_TESTING.md).
