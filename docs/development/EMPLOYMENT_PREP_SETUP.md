# Employment preparation setup (F5.3)

## Migrate

```bash
cd apps/api
alembic upgrade head
```

Expected head: `20261110_3600_f53`.

## Optional AI CV assist

Uses the shared LangGraph AI gateway. Feature flag / usage key: `ai.workflow.cv_wording`.

If the AI service is unavailable or the org flag/cap blocks use, the API returns a local cleanup suggestion that still requires tenant approval. CV Builder works without AI.

## Mobile

Tenant app routes:

- `/(app)/employment` — hub
- `/(app)/employment-skills`
- `/(app)/employment-cvs` and `/(app)/employment-cv/[id]`
- `/(app)/employment-applications`
- `/(app)/employment-interview`
- `/(app)/employment-roadmap`

## Web staff summary

`/dashboard/employment-support?tenantId=<uuid>` — authorised staff only; limited summary fields.

## Tests

```bash
cd apps/api
pytest tests/test_f53_employment_prep.py -q
# With Postgres:
pytest tests/test_f53_employment_prep.py -q -m postgres
```
