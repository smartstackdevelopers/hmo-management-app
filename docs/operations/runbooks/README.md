# HMore operational runbooks (F7.9)

**Status:** Documentation prepared — **not** operationally approved until client sign-off.

Central index for operations, incident response, and recovery. Built from the **actual** monorepo architecture (Next.js `apps/web`, FastAPI `apps/api`, AI `apps/ai-service`, Expo `room-ready`, PostgreSQL, Redis/Celery, optional AWS Terraform F7.6).

| # | Document | Purpose |
| --- | --- | --- |
| 1 | [HMORE_OPERATIONS_RUNBOOK.md](./HMORE_OPERATIONS_RUNBOOK.md) | Architecture, dependencies, startup/shutdown, incident overview |
| 2 | [APPLICATION_OPERATIONS.md](./APPLICATION_OPERATIONS.md) | Web, API, AI, mobile troubleshooting |
| 3 | [SECURITY_INCIDENT_RESPONSE_PLAN.md](./SECURITY_INCIDENT_RESPONSE_PLAN.md) | Security incident lifecycle |
| 4 | [PERSONAL_DATA_BREACH_RESPONSE_PLAN.md](./PERSONAL_DATA_BREACH_RESPONSE_PLAN.md) | UK GDPR breach process (DPO/legal review required) |
| 5 | [DISASTER_RECOVERY_RUNBOOK.md](./DISASTER_RECOVERY_RUNBOOK.md) | Recovery sequence (F7.3 backup/restore) |
| 6 | [DATABASE_OPERATIONS_GUIDE.md](./DATABASE_OPERATIONS_GUIDE.md) | PostgreSQL health, migrations, restore |
| 7 | [AWS_INFRASTRUCTURE_OPERATIONS_GUIDE.md](./AWS_INFRASTRUCTURE_OPERATIONS_GUIDE.md) | Prepared ECS/RDS/S3 ops (F7.6) |
| 8 | [DEPLOYMENT_AND_ROLLBACK_GUIDE.md](./DEPLOYMENT_AND_ROLLBACK_GUIDE.md) | Release, migration gates, rollback |
| 9 | [MONITORING_AND_ALERTING_GUIDE.md](./MONITORING_AND_ALERTING_GUIDE.md) | Health endpoints, Sentry, backup dashboard |
| 10 | [USER_ACCESS_ADMINISTRATION_GUIDE.md](./USER_ACCESS_ADMINISTRATION_GUIDE.md) | Auth0, MFA, six roles, sessions |
| 11 | [OPERATIONAL_CHECKLISTS.md](./OPERATIONAL_CHECKLISTS.md) | Daily / weekly / monthly checks (proposed) |
| 12 | [INCIDENT_SEVERITY_AND_ESCALATION.md](./INCIDENT_SEVERITY_AND_ESCALATION.md) | Severity, escalation placeholders |

## Related (other phases)

| Area | Path |
| --- | --- |
| F7.1 security | `docs/phase7/F7.1_SECURITY_TESTING_REMEDIATION.md` |
| F7.2 privacy / DPIA | `docs/phase7/privacy/` |
| F7.3 backup | `docs/operations/BACKUP_ARCHITECTURE.md`, `DATABASE_RESTORE_PROCEDURE.md` |
| F7.6 infrastructure | `docs/operations/infrastructure/` |
| F7.8 training | `docs/training/` |
| Occupancy gate | `docs/phase7/privacy/ROOM_OCCUPANCY_PRIVACY_REVIEW.md` |

## Document control (configure per organisation)

| Field | Value |
| --- | --- |
| Version | 1.0 (F7.9) |
| Document owner | **PENDING APPROVAL** |
| Next review date | **PENDING APPROVAL** |
| Operational approval | **PENDING APPROVAL** |
