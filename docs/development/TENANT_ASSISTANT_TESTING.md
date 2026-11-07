# F3.10 Tenant Assistant — testing

## Unit

```powershell
cd apps/api
python -m pytest tests/test_f310_tenant_assistant_unit.py -q
```

## PostgreSQL

```powershell
cd apps/api
python -m pytest tests/test_f310_tenant_assistant.py -q
```

Requires `DATABASE_URL`. Skipped when unset.

## AI service (mocked)

```powershell
cd apps/ai-service
python -m pytest tests/test_tenant_assistant.py -q
```

## Frontend helpers

```powershell
cd apps/web
npx playwright test e2e/tenant-assistant.spec.ts
```

## Manual pilot config

Set `TENANT_ASSISTANT_PILOT_ORGANISATION_IDS` to the pilot organisation UUID before testing ask flows.
