# F1.10 Occupancy survey testing

```text
cd apps/api
pytest tests/test_f110_occupancy_survey.py tests/test_rbac_registry.py -q
# With DATABASE_URL:
pytest tests/test_f110_occupancy_survey.py tests/test_db_schema.py -q
```

PostgreSQL-marked tests skip without `DATABASE_URL`. Skipped ≠ passed.
