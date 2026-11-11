# Community directory setup (F5.1)

## Migrate

From the repo root (with API venv active):

```bash
cd apps/api
alembic upgrade head
```

Expected head: `20261110_3400_f51`.

## Create a listing (admin)

1. Sign in to the web dashboard as organisation admin or super admin.
2. Open **Community directory**.
3. Create a listing. Leave unknown fields blank — do not invent hours or eligibility.
4. Use **Verify listing** only after checking the source.
5. Publish is applied on verify when `publish=true` (default).

## Tenant view

1. Open the Tenant Mobile App Community / Local services screen.
2. Filter by Food bank, Community kitchen, or Clothing bank.
3. Search by name; open a listing for full details and verification status.

## Tests

```bash
cd apps/api
pytest tests/test_f51_community_directory.py tests/test_f41_tenant_mobile.py -q
```

PostgreSQL-backed tests require the configured test database (`pytest.mark.postgres`).
