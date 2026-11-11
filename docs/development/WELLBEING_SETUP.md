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

Account → Community and career → My wellbeing, or `/(app)/wellbeing`.

Routines support categories, recurrence, optional reminders (`reminder_enabled` via F4.3 push), edit/delete, and complete/skip. History supports week/month ranges, a non-clinical mood overview, and delete.

## Web

`/dashboard/wellbeing-resources` for authorised staff to manage exercise/mindfulness and directory entries.

## Tests

```bash
cd apps/api
pytest tests/test_f55_wellbeing.py -q -m "not postgres"
pytest tests/test_f55_wellbeing.py -q -m postgres
```
