# F3.5 Case summaries testing

## Unit (no database, no LLM)

```bash
cd apps/api
pytest tests/test_f35_case_summaries_unit.py -q

cd ../ai-service
pytest tests/test_case_summary.py -q
```

## Frontend

Playwright covers view helpers, permission gating, responsive layout classes, and that the route responds without a server error when signed out:

```bash
cd apps/web
npx playwright test e2e/case-summaries.spec.ts
```

## PostgreSQL

```bash
cd apps/api
pytest tests/test_f35_case_summaries.py -m postgres -q
```

Requires `TEST_DATABASE_URL` or `DATABASE_URL` and a migrated database. These tests call the service with `AI_SERVICE_BASE_URL` empty (grounded composer) or with the AI client monkeypatched. They do **not** call OpenAI.

## What each suite is

| Suite | Kind |
| --- | --- |
| `test_f35_case_summaries_unit.py` | Unit. Grounded composer, validation, RBAC matrix, feature id |
| `test_case_summary.py` | Mocked / heuristic AI workflow. `LLM_PROVIDER=none`. Not a real provider |
| `test_f35_case_summaries.py` | Real PostgreSQL when a database is available. AI client mocked for failure cases |
| `e2e/case-summaries.spec.ts` | Frontend helpers and unauthenticated route smoke |
| OpenAI, Redis cache hit, Celery | Not part of this acceptance run |

Do not report the heuristic or monkeypatched client as a live model integration.
