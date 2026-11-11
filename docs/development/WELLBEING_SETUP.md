# Wellbeing setup (F5.5)

## Migrate

```bash
cd apps/api
alembic upgrade head
```

Expected head: `20261110_3800_f55`.

## Permissions

- Tenants: `wellbeing.manage.own`
- Org admins: `wellbeing.resources.manage` (resource/directory admin only — not private mood notes)

## Mobile

Account → My wellbeing, or `/(app)/wellbeing`.

## Web

`/dashboard/wellbeing-resources` for authorised staff to manage exercise/mindfulness and directory entries.

## Tests

```bash
cd apps/api
pytest tests/test_f55_wellbeing.py -q -m "not postgres"
pytest tests/test_f55_wellbeing.py -q -m postgres
```
