# Disaster recovery runbook

Uses verified F7.3 backup design. **RPO / RTO: PENDING APPROVAL — NOT VERIFIED** in production until client sign-off and drill evidence.

## Recovery objectives

| Metric | Status | Notes |
| --- | --- | --- |
| RPO | **PENDING APPROVAL** | Hourly Celery backup dispatch when `BACKUP_ENABLED=true` |
| RTO | **PENDING APPROVAL** | Depends on RDS restore size and operator staffing |
| Last verified drill | **NOT VERIFIED** in production | See F7.3 report — partial isolated drill |

## Service recovery sequence (recommended)

1. **Assess** scope — partial vs full region loss.
2. **Communicate** — incident severity Critical; tenant messaging approval.
3. **Network / DNS** — ALB or alternate endpoint **when AWS live**.
4. **PostgreSQL** — restore to **new** instance from verified `backup_runs` (never in-place overwrite without approval).
5. **Redis** — rebuild empty cache; Celery queues may be lost — accept job loss or replay from DB state **PENDING APPROVAL**.
6. **S3 files** — restore from versioning/CRR **operator**; verify manifests from backup jobs.
7. **API + workers** — deploy known-good image; run `alembic upgrade head` only if manifest requires.
8. **AI service** — deploy; verify token and provider keys.
9. **Web** — deploy; verify Auth0 and API URL.
10. **Mobile** — no server component; verify API URL for clients.
11. **Post-recovery validation** (below).

## Database recovery

Follow `docs/operations/DATABASE_RESTORE_PROCEDURE.md` on an **isolated** database.

**Warning:** `pg_restore` over production `DATABASE_URL` is forbidden without executive + DPO approval and maintenance window.

Record drill via `restore_drill_runs` when `BACKUP_RESTORE_DRILL_ALLOWED=true`.

## File recovery

- Verify checksum on backup manifest JSON.
- Object-level restore from S3 versioning — operator IAM role separate from app role (`BACKUP_ARCHITECTURE.md`).

## Application recovery

- Prefer **rollback image** for code defects (see DEPLOYMENT guide).
- For data defects, restore DB/files — not git rollback alone.

## Redis recovery

- ElastiCache rebuild (Terraform module) or new Redis container.
- Expect cleared sessions cache; users may need re-login.

## Background worker recovery

1. Start Redis.
2. Start Celery worker + beat.
3. Monitor failed tasks in logs; re-queue critical jobs manually **PENDING APPROVAL** list.

## AI service recovery

1. Health check endpoints.
2. Verify LangGraph workflows registered.
3. Confirm human-approval queues consistent with DB state.

## Post-recovery validation

| Check | Pass criteria |
| --- | --- |
| `GET /health` | `ok` on API, AI |
| Auth smoke test | Staff login with MFA policy |
| Org isolation | Sample cross-org access denied |
| Backup dashboard | New backup run starts |
| Audit write | Test action logged |

Document results in external incident record. **Do not** claim DR tested unless drill evidence exists.

## What this runbook does not do

- Auto-failover — **not configured** by default in Terraform (`stack_enabled = false`).
- Cross-region active-active — **not implemented**.
