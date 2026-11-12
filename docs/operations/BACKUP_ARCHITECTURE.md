# HMore backup architecture (F7.3)

## Components

| Layer | Mechanism |
|-------|-----------|
| PostgreSQL | `pg_dump` custom format to `BACKUP_LOCAL_ROOT` and optional `BACKUP_S3_BUCKET` |
| Private files | Metadata manifest JSON (full object replication via AWS S3 versioning / cross-region replication — operator) |
| Config | Alembic head + public table count manifest |
| Scheduling | Celery `hmore.backup.dispatch_and_process` hourly when `BACKUP_ENABLED=true` |
| Monitoring | API `/api/v1/backups/dashboard`, web `/dashboard/backups` |

## Security

- Backups must use **private** buckets with SSE-S3 or SSE-KMS.
- Never commit backup artifacts or secrets to Git (see `.gitignore`).
- IAM roles: backup role separate from application S3 upload role.
- Super Admin only for backup management permissions.

## Retention

Configurable rows in `backup_retention_settings` (defaults are **pending organisational approval**).
