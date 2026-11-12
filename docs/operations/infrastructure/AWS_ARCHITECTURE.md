# AWS architecture (prepared)

**Region (preferred):** `eu-west-2` (London) — **PENDING APPROVAL**

**Provisioned:** **NO** (F7.6 default `stack_enabled = false`)

## Services

| Component | Target | Notes |
| --- | --- | --- |
| Web | ECS Fargate + ALB | `Dockerfile.web` |
| API | ECS Fargate + ALB | `Dockerfile.api` |
| AI | ECS Fargate (private) | `Dockerfile.ai` |
| Workers | ECS Fargate | `Dockerfile.worker` + beat task |
| PostgreSQL | RDS pg16 + pgvector | Private DB subnets, encryption |
| Redis | ElastiCache | TLS + private subnets |
| Files | S3 private SSE-KMS | Module `s3_private` |
| Secrets | Secrets Manager | Task injection at runtime |
| Identity | Auth0 (external) | UK/EU tenant alignment required |
| CI | GitHub Actions | `ci.yml` + `infra-validate.yml` |
| Monitoring | CloudWatch logs + optional Sentry | `SENTRY_DSN` |

Mobile (Expo) uses the same FastAPI backend over HTTPS.

## Cross-region transfers

None planned in primary design. DR to `eu-west-1` or another region requires DPIA + client approval.
