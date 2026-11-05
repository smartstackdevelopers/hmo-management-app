# Security Verification Checklist (F1.11)

Mark each row with evidence. Do not tick “done” without artefacts.

## Encryption

| Check | Status | Evidence |
| --- | --- | --- |
| RDS storage encryption enabled | Not verified in repo | AWS console / CLI |
| RDS backups encrypted | Not verified | AWS |
| S3 default encryption | Not verified | AWS |
| S3 Block Public Access | Not verified | AWS |
| Application-level field encryption | Not implemented | N/A Phase 1 |

## Secrets

| Check | Status | Evidence |
| --- | --- | --- |
| `.env` gitignored | Implemented | `.gitignore` |
| `.env.example` placeholders only | Implemented | Pytest `test_env_example_files_are_placeholders_only` |
| No secrets in `NEXT_PUBLIC_*` | Implemented (convention) | Web `.env.example` |
| Production missing config fails boot | Implemented | `Settings.production_validation_errors` + tests |
| Secrets Manager wired | Target only | Pending deploy |
| Log redaction helpers exist | Implemented | `app.core.secrets` |

## TLS / transport

| Check | Status | Evidence |
| --- | --- | --- |
| Public HTTPS edge | Target | Pending deploy |
| API→DB TLS | Target | Connection string `sslmode` |
| Cert validation enabled | Required | Never disable |

## Database / storage / IAM

| Check | Status | Evidence |
| --- | --- | --- |
| Postgres not public | Target | SG / subnet |
| Redis not public | Target | SG / subnet |
| Least-privilege IAM | Target | Policy review |
| Org RLS + app checks | Implemented | F1.5 tests (CI) |

## Logging / backup / deploy

| Check | Status | Evidence |
| --- | --- | --- |
| Audit framework | Implemented | F1.7 |
| Backup runbook | Documented | AWS target doc |
| Approved RPO/RTO | Missing | Client decision |
| Production deploy | Not in Phase 1 | Explicit non-goal |
