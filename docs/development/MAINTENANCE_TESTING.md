# Maintenance (F2.8) testing

## Backend

From `apps/api` with dependencies and `DATABASE_URL` set:

```bash
pytest -q tests/test_f28_maintenance.py
pytest -q -m postgres tests/test_f28_maintenance.py
```

The `@pytest.mark.postgres` integration test exercises create → acknowledge → assign → in-progress → complete, audit events, cross-organisation denial, and dashboard aggregation.

## Migrations

Apply the F2.8 revision:

```bash
cd apps/api && alembic upgrade head
```

## Frontend

```bash
cd apps/web && npm run typecheck && npm run lint
```

Playwright helper tests (`e2e/maintenance.spec.ts`) cover `maintenanceApi` badge helpers only — full E2E needs Auth0 + API.

## Manual checks

1. Organisation Admin: `POST /api/v1/maintenance/seed-defaults`, then create a request and walk transitions.
2. Verify tenant cannot set `emergency` priority on create.
3. Verify photograph download requires `maintenance.photo.read` and request access.
4. Verify emergency panels show placeholder warning until `approved_for_use` is set by an admin.
