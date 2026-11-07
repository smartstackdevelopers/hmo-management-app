# Communication platform testing (F2.12)

- **Unit / offline**: `pytest apps/api/tests/test_f212_communication.py` (postgres tests skip without `TEST_DATABASE_URL` or `DATABASE_URL`).
- **Provider smoke** (Postgres): `test_notification_provider_in_app_delivery` in `tests/test_f22_rota_visits_tasks.py` exercises in-app delivery row creation.
- **Migrations**: from `apps/api`, `alembic upgrade head` after setting `DATABASE_URL` (see `docs/development/DATABASE_MIGRATIONS.md`).
- **Celery**: worker registers `hmore.communication.dispatch_scheduled_reminders` (see `apps/api/app/workers/celery_app.py`).

Real SMTP, SMS, or translation APIs are **not** verified unless those env vars are set; defaults use test adapters.
