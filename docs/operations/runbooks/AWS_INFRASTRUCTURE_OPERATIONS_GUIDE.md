# AWS infrastructure operations guide

**Status:** Prepared for UK/EU target (F7.6). **No live stack by default** — `stack_enabled = false` in `infra/aws/terraform/`.

## Scope

Documents **prepared** topology only. Do not operate resources that have not been provisioned.

Reference: `docs/operations/infrastructure/AWS_ARCHITECTURE.md`, `NETWORK_ARCHITECTURE.md`.

## Services (when enabled)

| Service | Purpose |
| --- | --- |
| ECS Fargate | web, api, ai, Celery worker, beat |
| ALB | HTTPS termination, health checks on `/health` |
| RDS PostgreSQL | Primary database |
| ElastiCache Redis | Broker/cache |
| S3 | Private app + backup buckets |
| Secrets Manager | `DATABASE_URL`, tokens, keys |
| CloudWatch | Logs and alarms (module observability) |
| ECR | Container images |

## Common failures

| Alert / symptom | Likely cause | Safe steps |
| --- | --- | --- |
| ALB 5xx | Unhealthy targets | Check ECS task logs; verify health path |
| ECS task cycling | Bad env/secret | Roll back task definition image **not** DB |
| RDS storage full | Growth | Scale storage **PENDING APPROVAL** |
| Redis evictions | Memory pressure | Scale node; review cache TTL |
| S3 403 | IAM policy | Fix task role — no public ACL |

## Terraform operations

1. `terraform plan` in approved workspace — **human review required**.
2. `terraform apply` — **never from CI** (F7.6).
3. State: remote backend per `backend.tf.example` — **PENDING APPROVAL**.

**Warning:** `terraform destroy` is destructive — executive approval only.

## Region and compliance

Target region: **eu-west-2** (London). Data residency decisions **PENDING APPROVAL** per client contract.

## Cost and limits

See `COST_ESTIMATE.md` — estimates only, not billing truth.

## Escalation

**CONFIG_PLACEHOLDER — Cloud platform owner** for AWS account issues.
