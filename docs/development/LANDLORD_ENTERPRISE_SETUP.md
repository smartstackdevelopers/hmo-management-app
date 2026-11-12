# F6.1 Landlord enterprise setup

```bash
cd apps/api
alembic upgrade head
```

Expected head: `20261111_3900_f61`.

## Tests

```bash
cd apps/api
pytest tests/test_f61_landlord_enterprise.py -q -m "not postgres"
pytest tests/test_f61_landlord_enterprise.py -q -m postgres
```

## Web

Sign in as landlord → `/dashboard/landlord`.

Rent “recorded paid” requires an authorised note — there is no payment gateway in F6.1.
