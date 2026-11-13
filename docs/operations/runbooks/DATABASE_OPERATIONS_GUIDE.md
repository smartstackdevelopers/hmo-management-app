# Database and storage operations guide

## PostgreSQL

### Health checks

- Application: API starts without DB connection errors; `GET /api/v1/health` ok.
- RDS: CloudWatch CPU, storage, connections **when live**.
- CI pattern: `pg_isready` in GitHub Actions service container.

### Connection failures

1. Verify `DATABASE_URL` (Secrets Manager / env).
2. Security groups allow ECS → RDS **when AWS live**.
3. Max connections: reduce pool size or scale RDS **PENDING APPROVAL**.

### Slow queries

1. Use `/dashboard/performance` authorised probes (F7.4).
2. PostgreSQL `pg_stat_statements` **PENDING APPROVAL** extension on RDS.
3. Fix via migration/index — normal change control, not emergency DDL without review.

### Connection pool issues

- Uvicorn workers × pool size — align with RDS `max_connections`.
- Symptom: intermittent `too many connections` — scale down workers or up RDS.

### Backup verification

- Super Admin: `/dashboard/backups`
- API: `GET /api/v1/backups/dashboard`
- Confirm recent `backup_runs` with `verification_status=passed` where applicable.

### Database recovery

→ `docs/operations/DATABASE_RESTORE_PROCEDURE.md` and [DISASTER_RECOVERY_RUNBOOK.md](./DISASTER_RECOVERY_RUNBOOK.md).

### Migration failures

1. **Stop** further deploys.
2. Capture Alembic revision: `alembic current`.
3. Restore DB from pre-migration backup if data corrupted — **approval required**.
4. **Never** auto-run `alembic downgrade` in production without scripted review.

**Warning:** Destructive SQL (`DROP`, `TRUNCATE`) requires written approval and isolated environment.

---

## Redis and Celery

### Redis connectivity

- Env `REDIS_URL` on API, workers, AI cache.
- Symptom: API up but jobs stuck — check Redis ping.

### Queue monitoring

- Inspect Celery logs; queue depth custom metric **PENDING APPROVAL** (F7.6 observability notes).

### Worker failures

1. Restart worker container/task.
2. Check import errors in worker logs (code deploy mismatch).

### Failed background jobs

- Backup jobs record status in `backup_runs`.
- Retry policy per task — do not blindly `purge` queues in production.

### Scheduled tasks

- Celery beat must be running exactly once per environment (duplicate beat → duplicate schedules).

---

## S3 storage

### Upload failures

- API validates type/size (F1.8).
- IAM task role permissions on `PutObject` **production**.
- Local dev: storage backend configuration.

### Download failures

- Private objects — access via authorised API routes only.

### Permission issues

- Separate backup bucket role from application upload role (`BACKUP_ARCHITECTURE.md`).

### Availability

- AWS S3 regional endpoint `eu-west-2` target — status.aws.amazon.com.

### Backup verification

- Manifest JSON in backup jobs; operator verifies object listing.

### File recovery

Versioning / replication — operator procedure external to app; align with DR runbook.
