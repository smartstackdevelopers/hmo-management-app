# Operational checklists

**Proposed checklists only** — completing items below does not imply checks were already performed.

Tick boxes when executed; store completed copies outside Git if they contain environment-specific notes.

## Daily operations

| Check | How | Owner |
| --- | --- | --- |
| [ ] Application health | `/health` web + API | Operator |
| [ ] API availability | Synthetic probe or manual | Operator |
| [ ] Database health | No connection errors in logs | Operator |
| [ ] Background jobs | Celery/backup last run ok | Operator |
| [ ] Error alerts | Sentry new issues triaged | Operator |
| [ ] Backup status | `/dashboard/backups` if enabled | Super Admin |
| [ ] Security alerts | Auth failure review **PENDING APPROVAL** threshold | Security |

## Weekly operations

| Check | How |
| --- | --- |
| [ ] Failed job review | Celery logs + `backup_runs` failures |
| [ ] Access review sample | New memberships / role changes in audit |
| [ ] Error trend | Sentry weekly digest |
| [ ] Storage review | S3 usage / local disk for dev backups |
| [ ] Backup verification | Latest run `verification_status` |

## Monthly operations

| Check | How |
| --- | --- |
| [ ] Security review | F7.1 checklist spot-check |
| [ ] User access review | Organisation Admin per org policy |
| [ ] Backup restore drill | Isolated `pg_restore --list` or full drill **PENDING APPROVAL** schedule |
| [ ] Dependency review | npm/pip audit — change control for upgrades |
| [ ] Incident trend | Ticket system export |
| [ ] Retention policy | F7.2 retention template vs practice |

## Room occupancy (when gate approved)

| Check | How |
| --- | --- |
| [ ] Device connectivity | Vendor/edge monitoring **PENDING APPROVAL** |
| [ ] Privacy signage | Organisation compliance |
| [ ] Access logs | Occupancy corrections audited |
| [ ] No bedroom cameras | Site survey affirmations |

Live ingest remains **BLOCKED** until gate approved in product.
