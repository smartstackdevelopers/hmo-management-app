# F3.12 operational search testing

## Unit (no database)

```powershell
cd apps/api
python -m pytest tests/test_f312_operational_search_unit.py -q
```

```powershell
cd apps/ai-service
python -m pytest tests/test_operational_search.py -q
```

These tests check interpretation, SQL rejection, tenant denial, and organisation-scoped cache keys. They do not call a live model.

## PostgreSQL

```powershell
cd apps/api
python -m pytest tests/test_f312_operational_search.py -m postgres -q
```

Real database coverage: open complaints, closed rows excluded, support-worker assignment filter, other-organisation rows excluded. AI is not configured in this test (`interpretation_source` is deterministic).

## Frontend helpers

```powershell
cd apps/web
npx playwright test e2e/operational-search.spec.ts
```
