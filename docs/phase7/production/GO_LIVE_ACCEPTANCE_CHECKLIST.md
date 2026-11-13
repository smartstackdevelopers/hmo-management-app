# Go-Live acceptance checklist (post-deploy template)

Use **after** an approved deployment. **This run:** all items **BLOCKED** / **NOT VERIFIED** — no production deploy.

| # | Criterion | Status | Evidence required |
| --- | --- | --- | --- |
| 1 | Production web accessible | **NOT VERIFIED** | HTTPS URL + 200 |
| 2 | Backend APIs operational | **NOT VERIFIED** | `/health`, `/api/v1/health` |
| 3 | AI service operational | **NOT VERIFIED** | AI `/health` |
| 4 | PostgreSQL healthy | **NOT VERIFIED** | RDS metrics |
| 5 | Redis + Celery healthy | **NOT VERIFIED** | Queue depth, beat running |
| 6 | Private S3 uploads/downloads | **NOT VERIFIED** | Test file round-trip |
| 7 | Monitoring active | **NOT VERIFIED** | Sentry + CloudWatch alarms |
| 8 | Backups configured | **NOT VERIFIED** | `backup_runs` in prod |
| 9 | Authentication works | **NOT VERIFIED** | Auth0 prod tenant smoke |
| 10 | Six-role permissions | **NOT VERIFIED** | Smoke script § roles |
| 11 | Organisation isolation | **NOT VERIFIED** | Cross-org deny test |
| 12 | Critical user journeys | **NOT VERIFIED** | `SMOKE_TEST_SCRIPT.md` |
| 13 | Mobile prod API connectivity | **NOT VERIFIED** | Approved EAS prod build |
| 14 | Operational docs available | **PASS** | `docs/operations/runbooks/` |
| 15 | Security + privacy approvals recorded | **PENDING APPROVAL** | Signed gate form |

**Go-Live accepted:** ☐ No — deployment **BLOCKED**
