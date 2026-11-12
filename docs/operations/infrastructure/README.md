# HMore production infrastructure (F7.6)

Prepared only — **no live AWS provisioning** from this phase without client approval.

| Document | Purpose |
| --- | --- |
| [AWS_ARCHITECTURE.md](./AWS_ARCHITECTURE.md) | Service topology in `eu-west-2` |
| [NETWORK_ARCHITECTURE.md](./NETWORK_ARCHITECTURE.md) | VPC, subnets, security groups |
| [DEPLOYMENT_RUNBOOK.md](./DEPLOYMENT_RUNBOOK.md) | ECS/Docker rollout steps (manual approval) |
| [SECRETS_AND_MONITORING.md](./SECRETS_AND_MONITORING.md) | Secrets Manager, Sentry, CloudWatch |
| [CICD_DEPLOYMENT.md](./CICD_DEPLOYMENT.md) | CI vs production deploy gates |
| [ROLLBACK_PLAN.md](./ROLLBACK_PLAN.md) | Roll back tasks/images without data loss |
| [COST_ESTIMATE.md](./COST_ESTIMATE.md) | **Estimates** — not actual bills |

Terraform: `infra/aws/terraform/` (`stack_enabled = false` by default).
