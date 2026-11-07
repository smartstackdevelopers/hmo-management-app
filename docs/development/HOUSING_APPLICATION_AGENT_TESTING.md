# F3.8 housing application analysis testing

## Unit (no database, no LLM)

```bash
cd apps/api
pytest tests/test_f38_housing_application_analysis_unit.py -q

cd ../ai-service
pytest tests/test_housing_application_analysis.py -q
```

## PostgreSQL

```bash
cd apps/api
pytest tests/test_f38_housing_application_analysis.py -m postgres -q
```

These tests use the local checklist evaluator. The AI client is monkeypatched for the usage-cap case. They assert that analysis does not approve, reject, or change waiting-list state.

## Frontend

```bash
cd apps/web
npx playwright test e2e/housing-application-analysis.spec.ts
```

## What was not tested as a live integration

- OpenAI
- Redis cache hits
- Celery
- A signed-in browser click through Analyse, Confirm, and Mark reviewed
