# Monitoring and alerting guide

Documents **configured or prepared** tooling in HMore — not all alerts are live until AWS/Sentry approved.

## Tools

| Tool | Scope | Activation |
| --- | --- | --- |
| Health endpoints | Liveness | Always in code |
| Sentry | API, AI errors | `SENTRY_DSN` set |
| CloudWatch | ECS/RDS logs | Terraform `observability` when `stack_enabled` |
| Backup dashboard | Backup jobs | F7.3 when `BACKUP_ENABLED` |
| Performance dashboard | F7.4 probes | Authorised web users |
| GitHub Actions CI | Test regressions | On push/PR |
| Auth0 | Auth anomalies | External dashboard |

Web Sentry client DSN **PENDING APPROVAL**.

## Alert catalogue (prepared meanings)

| Signal | Severity | Possible cause | Investigation | Escalation |
| --- | --- | --- | --- | --- |
| `/health` fail | Critical | Process down, deploy fail | ECS/logs; restart task | Technical on-call |
| API 5xx rate | High | Bug, DB, dependency | Sentry stack traces | Release manager |
| DB connection errors | High | URL, RDS, pool | Secrets, RDS metrics | DBA |
| Redis down | High | ElastiCache/network | Connectivity test | Platform |
| Celery queue depth high | Medium | Worker stopped, slow task | Worker logs | Technical |
| AI 503 | Medium | Token, provider, flags | AI health, secrets | AI owner |
| Backup run failed | High | S3 IAM, disk | `/dashboard/backups` | Super Admin + ops |
| Auth failure spike | Medium–High | Attack, IdP issue | Auth0 logs | Security |
| S3 upload errors | Medium | IAM, size limit | API logs | Technical |
| ALB 5xx | Critical | Unhealthy targets | Target group health | Platform |

Response time targets: **PENDING APPROVAL**.

## Safe resolution

1. Confirm alert not false positive (deploy in progress).
2. Follow [APPLICATION_OPERATIONS.md](./APPLICATION_OPERATIONS.md).
3. Escalate per severity matrix.
4. Document resolution in ticket **CONFIG_PLACEHOLDER**.

## Performance issues

- F7.4 journey probes and gzip/audit index optimisations documented in `F7.4_PERFORMANCE_FINAL_REPORT.md`.
- Scale horizontally **PENDING APPROVAL** capacity plan.

## Security alerts

- Route to [SECURITY_INCIDENT_RESPONSE_PLAN.md](./SECURITY_INCIDENT_RESPONSE_PLAN.md).
- Preserve evidence before remediation.

## Backup failures

1. Open backup dashboard.
2. Read `backup_runs` error message.
3. Fix IAM or local `BACKUP_LOCAL_ROOT` path.
4. Manual trigger **PENDING APPROVAL** procedure.
