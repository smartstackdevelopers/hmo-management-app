# Database migrations

Tooling: Alembic inside `apps/api`.

## Layout

```text
apps/api/alembic.ini
apps/api/alembic/env.py
apps/api/alembic/versions/20261105_1200_f12_initial_phase1_schema.py
apps/api/alembic/versions/20261105_1500_f14_authorization_version.py
apps/api/alembic/versions/20261105_1600_f15_organisation_isolation_rls.py
apps/api/alembic/versions/20261105_1700_f15_rls_app_role.py
apps/api/alembic/versions/20261105_1800_f16_core_record_fields.py
```

`env.py` loads SQLAlchemy metadata from `app.db.models` and reads `DATABASE_URL` from application settings. Hardcoded credentials are not used.

Current head: `20261105_1800_f16` (tenant consent/preferences/needs fields + room type/notes for F1.6).

## Naming

Revision files use:

```text
YYYYMMDD_HHMM_f12_<short_slug>.py
```

The initial revision id is `20261105_1200_f12`.

## Commands

Run from `apps/api` with dependencies installed and `DATABASE_URL` set:

```text
alembic upgrade head
alembic downgrade -1
alembic downgrade base
alembic current
alembic history
```

Generate a new revision after model changes (review the script before applying):

```text
alembic revision --autogenerate -m "f12 describe change"
```

Never edit the live database by hand without a matching Alembic revision.

## Initial migration behaviour

Revision `20261105_1200_f12`:

1. `CREATE EXTENSION IF NOT EXISTS vector`
2. Creates enums `hmore_role`, `membership_status`, `record_status`
3. Creates Phase 1 tables, constraints, and indexes
4. Downgrade drops the tables and enums; it leaves the `vector` extension installed

## Validation

- Local: `alembic upgrade head` against the Compose pgvector database, then `pytest -q`
- CI: the API job starts `pgvector/pgvector:pg16`, runs `alembic upgrade head`, then Pytest including schema tests

SQLite is rejected by `alembic/env.py` and by the test suite.
