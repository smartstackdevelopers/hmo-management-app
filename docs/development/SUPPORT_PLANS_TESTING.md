# F2.10 Support Plans — Testing

## Backend

From `apps/api` with dependencies installed:

```bash
pytest tests/test_f210_support_plans.py -v
pytest tests/test_rbac_registry.py tests/test_rbac_authorization.py -v
```

- `test_f210_support_plans.py` is marked `@pytest.mark.postgres` — requires `DATABASE_URL` or `TEST_DATABASE_URL` pointing at PostgreSQL with migrations applied (`alembic upgrade head`).

## Integration checks

- Apply migration `20261106_2100_f210_support_plans` and confirm RLS policies exist on all `support_plan_*` and `tenant_support_plans` tables.
- Exercise plan status transitions: `draft` → `active` → `on_hold` → `active`, `complete`, `close`.
- Confirm `PATCH` on a **finalised** review returns 409.
- Confirm organisation B cannot read organisation A plans (404/403).

## Frontend / E2E

- `apps/web`: `npm run lint`, `npm run typecheck`.
- Playwright: `npm run test:e2e` (includes `e2e/support-plans.spec.ts` navigation filter smoke).
