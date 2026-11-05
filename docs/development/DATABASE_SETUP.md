# Database setup

## Requirements

- PostgreSQL 16+ with the **pgvector** extension available
- Recommended local image: `pgvector/pgvector:pg16` via Compose
- Python 3.12 and the `apps/api` virtualenv dependencies

Docker Desktop is optional but is the supported way to run the pgvector image on a developer machine. A vanilla PostgreSQL install without pgvector cannot apply the F1.2 migration, because the migration runs `CREATE EXTENSION vector`.

## Compose (preferred)

From the repository root:

```text
docker compose -f infra/docker/docker-compose.yml up -d postgres
```

Default local credentials (examples only, never for production):

| Variable | Value |
| --- | --- |
| POSTGRES_DB | hmore |
| POSTGRES_USER | hmore |
| POSTGRES_PASSWORD | hmore |
| Host port | 5432 |

API URL:

```text
DATABASE_URL=postgresql+psycopg://hmore:hmore@localhost:5432/hmore
```

Copy `apps/api/.env.example` to `apps/api/.env` and adjust if needed. Do not commit `.env`.

## Install Python database dependencies

```text
cd apps/api
pip install -r requirements.txt
```

## Apply migrations

```text
cd apps/api
alembic upgrade head
```

See `docs/development/DATABASE_MIGRATIONS.md`.

## Connection check

```text
cd apps/api
python -c "from app.db.session import check_database_connection, reset_engine_cache; reset_engine_cache(); print(check_database_connection())"
```

Requires `DATABASE_URL` in the environment or `apps/api/.env`.

## Test database

Use a separate database so pytest does not touch developer data:

```text
CREATE DATABASE hmore_test;
```

```text
set TEST_DATABASE_URL=postgresql+psycopg://hmore:hmore@localhost:5432/hmore_test
cd apps/api
pytest -q
```

If neither `TEST_DATABASE_URL` nor `DATABASE_URL` is set, health tests still run and PostgreSQL schema tests are skipped.

GitHub Actions creates an isolated `hmore_test` database with the pgvector image for every API job.

## Room Ready SQLite

Do not set `DATABASE_URL` to the Node API SQLite file. Prisma migrations under `api/prisma` stay with the reference application.
