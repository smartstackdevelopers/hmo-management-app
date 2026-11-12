# PostgreSQL restore procedure (operator)

**Warning:** Perform only on an **isolated** database instance. Never restore over production `DATABASE_URL`.

## Prerequisites

- Verified `backup_runs` row with `status=verified` and `verification_status=passed`
- `pg_restore` client tools
- Empty target database

## Steps

1. Copy backup artifact from private storage to restore host (encrypted transfer).
2. Verify SHA256 against `checksum_sha256` in `backup_runs`.
3. `pg_restore --list` on custom-format dump — must succeed.
4. Create empty database and role `hmore_app` per migrations.
5. `pg_restore --no-owner --role=hmore_app -d <target_db> <dumpfile>`
6. `alembic upgrade head` if manifest head differs.
7. Run organisation isolation smoke tests.
8. Record drill in `restore_drill_runs` via API when `BACKUP_RESTORE_DRILL_ALLOWED=true`.
