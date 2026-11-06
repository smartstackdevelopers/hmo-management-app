# Database migrations

Tooling: Alembic inside `apps/api`.

## Layout

```text
apps/api/alembic.ini
apps/api/migrations/env.py
apps/api/migrations/versions/20261105_1200_f12_initial_phase1_schema.py
apps/api/migrations/versions/20261105_1500_f14_authorization_version.py
apps/api/migrations/versions/20261105_1600_f15_organisation_isolation_rls.py
apps/api/migrations/versions/20261105_1700_f15_rls_app_role.py
apps/api/migrations/versions/20261105_1800_f16_core_record_fields.py
apps/api/migrations/versions/20261105_1900_f17_audit_framework.py
apps/api/migrations/versions/20261105_2000_f18_file_storage_metadata.py
apps/api/migrations/versions/20261105_2100_f110_occupancy_survey.py
… (Phase 2 revisions through F2.5)
apps/api/migrations/versions/20261106_1700_f26_evidence_packs.py
apps/api/migrations/versions/20261106_1800_f27_complaints.py
apps/api/migrations/versions/20261106_1900_f28_maintenance.py
apps/api/migrations/versions/20261106_2200_f211_document_management.py
apps/api/migrations/versions/20261106_2300_f212_communication_platform.py
```

The environment directory is named `migrations` (not `alembic`) so Python never imports the local script folder instead of the **`alembic`** PyPI package when running tests or tools from `apps/api`.

`env.py` loads SQLAlchemy metadata from `app.db.models` and reads `DATABASE_URL` from application settings. Hardcoded credentials are not used.

Current head includes `20261106_2300_f212_communication_platform` (F2.12 communication platform + RLS; migrates legacy `reminder_records.channel` from `log` to `in_app`).

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
