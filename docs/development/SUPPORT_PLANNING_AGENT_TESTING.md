# F3.7 support planning draft testing

## Unit (no database, no LLM)

```bash
cd apps/api
pytest tests/test_f37_support_plan_drafts_unit.py -q

cd ../ai-service
pytest tests/test_support_plan_draft.py -q
```

## PostgreSQL

```bash
cd apps/api
pytest tests/test_f37_support_plan_drafts.py -m postgres -q
```

These tests use the local draft composer. The AI client is monkeypatched for the usage-cap case. They do not call OpenAI.

## Frontend

```bash
cd apps/web
npx playwright test e2e/support-plan-drafts.spec.ts
```

## What was not tested as a live integration

- OpenAI
- Redis cache hits
- Celery
- A signed-in browser click through Generate, Approve, and Apply
