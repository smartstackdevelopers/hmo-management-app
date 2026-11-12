# Infrastructure cost estimate (assumptions only)

**These are planning figures, not AWS invoices.** Validate with AWS Pricing Calculator after region/account approval.

Assumptions: `eu-west-2`, moderate early production load, single-AZ Redis, multi-AZ RDS optional, NAT enabled.

| Item | Assumption | Est. monthly (USD) |
| --- | --- | --- |
| ECS Fargate (4 services, 0.5 vCPU / 1GB avg) | 4 tasks | 120–250 |
| RDS PostgreSQL db.t4g.medium, 50GB | Single-AZ | 80–140 |
| ElastiCache cache.t4g.small | 1 node | 25–45 |
| NAT Gateway | 1 AZ + data | 35–90 |
| ALB | 1 | 20–35 |
| S3 + requests | 500GB storage | 15–40 |
| CloudWatch logs | 30-day retention | 10–30 |
| Secrets Manager | ~10 secrets | 5–10 |
| Data transfer | Low | 10–50 |

**Rough total:** **~350–700 USD/month** at stated assumptions.

Excludes: Auth0, OpenAI/LLM usage, Sentry plan, domain/ACM (free cert), support contracts, staff time.

Variable drivers: tenant count, file storage, AI tokens, Celery volume, multi-AZ RDS, NAT.
