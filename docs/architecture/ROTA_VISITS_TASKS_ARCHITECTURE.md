# Rota, Visits, Tasks & Reminders (F2.2)

## Scope

Staff rota, tenant visit scheduling, operational tasks, and Celery+Redis reminder foundation. Integrates with F2.1 caseload assignment for Support Worker tenant access. No F2.12 communication providers, no AI, no mobile.

## Data model

| Table | Purpose |
| --- | --- |
| `staff_shifts` | Org-scoped staff shifts with overlap prevention |
| `tenant_visits` | Scheduled visits with controlled status transitions |
| `operational_tasks` | Assignable tasks with priority / due dates |
| `reminder_records` | Idempotent reminder schedule + delivery attempts |

All tables use organisation RLS.

## Celery + Redis

- Broker/backend: `REDIS_URL` (existing settings).
- App: `app.workers.celery_app.celery_app`
- Tasks: `hmore.reminders.dispatch_due`, `hmore.reminders.dispatch_organisation`
- Beat: every 60s dispatch due reminders.

Worker:

```bash
cd apps/api
celery -A app.workers.celery_app.celery_app worker -l info
celery -A app.workers.celery_app.celery_app beat -l info
```

## Reminder delivery

`app.ops.notifications.LogNotificationProvider` logs delivery only. External email/SMS/in-app is **F2.12**. Reminder rows still track pending/sent/failed/skipped with idempotency keys.

Lead times (env):

- `REMINDER_SHIFT_LEAD_MINUTES` (default 60)
- `REMINDER_VISIT_LEAD_MINUTES` (default 120)
- `REMINDER_TASK_DUE_LEAD_MINUTES` (default 1440)

## Authorisation

- Org Admin: manage rota (`organisation.users.manage`), visits/tasks oversight (`tenants.manage` + visits/tasks permissions).
- Support Worker: own shifts; own visits/tasks; assigned caseload tenants only for tenant-linked records.
- Landlords/Tenants: no access to these APIs.

## APIs

`/api/v1/shifts`, `/api/v1/visits`, `/api/v1/tasks`, `/api/v1/reminders`
