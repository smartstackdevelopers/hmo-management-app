# Encryption and Security Architecture (F1.11)

Phase 1 baseline. Distinguishes **implemented in-repo controls** from **target AWS controls not yet deployed**.

## Current posture (repository)

| Area | Current implementation | Required control | Gap | Recommended next step | Verification |
| --- | --- | --- | --- | --- | --- |
| Next.js web | Auth0 SDK; no secrets in `NEXT_PUBLIC_*` except non-secret base URL | TLS to users; secure cookies via Auth0 | Prod TLS termination not deployed here | ALB/CloudFront TLS in UK/EU | Browser HTTPS + cookie flags |
| Expo mobile | Auth0 native config; SecureStore for tokens | TLS; secure storage | Live tenant MFA unverified | Complete Auth0 UK/EU MFA checklist | Device login test |
| FastAPI | JWT validation via Auth0 JWKS; RBAC; org RLS; production config guard | TLS to clients; no public OpenAPI in prod | Edge TLS not in repo | API behind HTTPS load balancer | TLS scan + boot with `ENVIRONMENT=production` |
| PostgreSQL | Schema + RLS + `hmore_app` role | Encryption at rest + encrypted backups | No managed DB in repo | RDS/Aurora with storage encryption + KMS | AWS console / CLI evidence |
| pgvector | Extension in migrations | Same as Postgres | Same | Same | Same |
| Auth0 | Configured when env present | MFA for staff; UK/EU tenant | Live MFA unverified | Human Auth0 verification | Staff MFA challenge |
| Redis/Celery | URL config only | TLS in transit in prod; auth | Not hardened in Phase 1 deploy | ElastiCache in private subnet + AUTH/TLS | Network + AUTH test |
| S3 storage | Adapter + private ACL policy guidance | SSE-S3/SSE-KMS; Block Public Access | Bucket not provisioned by this PR | Private bucket + SSE + IAM role | Bucket policy + encryption status |
| CI/CD | GitHub Actions | No secrets in logs; OIDC to AWS later | No AWS deploy | OIDC deploy role | Workflow review |
| Logging | Application logs; audit events | Redact secrets | Not all log sinks reviewed | Central logs + redaction | Secret scan of samples |
| Audit | F1.7 append-oriented events | Retain as evidence | Retention policy undecided | Client retention decision | Policy doc |

## Encryption at rest

### PostgreSQL (target)

- Use AWS RDS/Aurora with **storage encryption enabled** (AWS KMS CMK preferred).
- Encrypt automated and manual backups with the same CMK strategy.
- Store DB credentials in **AWS Secrets Manager**; rotate via IAM-restricted roles.
- Do **not** expose Postgres publicly; private subnets only.
- **Status:** Target — not provisioned by F1.11.

### Private object storage (target + app readiness)

- Private bucket; Block Public Access on.
- Default encryption SSE-S3 or SSE-KMS.
- Prefer IAM task/instance roles over long-lived access keys (app allows keys both omitted).
- **Status:** Application adapter ready (F1.8); AWS bucket encryption **unverified** until provisioned.

### Application-level field encryption

- Phase 1 relies on transport + platform at-rest encryption for most fields.
- Highly sensitive fields may need application-level encryption later — list as a product decision.
- **Status:** Not implemented as app-level CMEK field encryption.

## Encryption in transit

| Hop | Requirement | Status |
| --- | --- | --- |
| Browser → web | HTTPS TLS 1.2+ | Target (edge) |
| Web/mobile → API | HTTPS; validate certs | Target (edge); local HTTP OK for development |
| API → Postgres | TLS (`sslmode=require`+) in production | Target |
| API → Redis | TLS where supported | Target |
| API → S3 | HTTPS AWS/S3 API | Adapter uses TLS endpoints by default |
| Service ↔ service | Private network + TLS where applicable | Target |

**Do not** disable certificate validation to make integrations work.

## Application security controls implemented in F1.11

- Production configuration validation (`Settings.production_validation_errors`).
- CORS allow-list (no `*` in production).
- Security headers middleware (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, conditional HSTS).
- OpenAPI/docs disabled when `ENVIRONMENT=production`.
- Secret redaction helpers for logs/diagnostics.
- `.env` gitignored; `.env.example` placeholders only.

## Sensitive data categories (Phase 1)

| Category | Examples | Handling |
| --- | --- | --- |
| Credentials | DB passwords, Auth0 secrets, S3 keys | Secrets Manager / IAM; never in git or `NEXT_PUBLIC_*` |
| Identity tokens | Access/refresh tokens | Auth0 session; never log |
| PII | Tenant names, emails, addresses | Org isolation + least privilege + audit |
| Evidence files | Survey attachments | Private storage + RBAC |
| Audit evidence | `audit_events` | Append-oriented privileges |

## Known limitations

- No live AWS account encryption proof in this repository.
- Auth0 MFA remains **unverified** until a real UK/EU tenant exercise.
- Backup RPO/RTO not client-approved.
- Data residency claims require confirmed region + subprocessors review — not asserted as complete.
