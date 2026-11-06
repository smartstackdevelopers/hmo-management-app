# F2.7 Complaints — Testing

## Backend

```text
cd apps/api
pytest tests/test_f27_complaints_workflow.py -q
pytest tests/test_f27_complaints_workflow.py -q -m postgres
```

Covers permissions, transitions, overdue helper, API 401, Celery task registration, and (with Postgres) create/review/notes privacy/escalation idempotency/org isolation/maintenance deny.

## Frontend

```text
cd apps/web
npx playwright test e2e/complaints.spec.ts
npm run typecheck
npm run lint
```

## Migration

```text
alembic upgrade head
```

Revision: `20261106_1800_f27`.
