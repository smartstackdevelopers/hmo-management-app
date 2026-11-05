# F1.7 Audit Testing

## Suites

| File | Kind |
| --- | --- |
| `tests/test_f17_audit.py` | Unit (matrix, redaction, 401) + Postgres audit/RLS/emergency |
| `tests/test_f16_records.py` | Regression — CRUD still audits via central service |
| `tests/test_organisation_isolation.py` | Regression — F1.5 isolation |
| `tests/test_rbac_*` | Regression — RBAC / assignment |
| `tests/test_db_schema.py` | Migration head includes `20261105_1900_f17` |

## Commands

```text
cd apps/api
pytest tests/test_f17_audit.py tests/test_rbac_registry.py tests/test_health.py -q

# With PostgreSQL (DATABASE_URL or TEST_DATABASE_URL):
pytest tests/test_f17_audit.py tests/test_db_schema.py tests/test_f16_records.py -q
```

PostgreSQL tests are marked `@pytest.mark.postgres` and **skip** when no database URL is configured. Skipped tests are not passed.

## Coverage map

1. Event creation + actor/org attribution  
2. Success / failure / denied outcomes  
3. Sensitive metadata redaction + oversized metadata rejection  
4. Pagination / filtering / cross-org denial helpers  
5. Append-oriented privileges for `hmore_app` (no UPDATE/DELETE)  
6. Emergency request + transitions logged without RBAC elevation  
7. Recursion guard  
8. Unauthenticated audit/emergency API → 401  
