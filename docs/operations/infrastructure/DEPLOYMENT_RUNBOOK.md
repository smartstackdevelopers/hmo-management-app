# Deployment runbook (prepared — not executed in F7.6)

## Preconditions

- [ ] Client approved region, domain, and cost estimate
- [ ] `stack_enabled = true` in approved `terraform.tfvars`
- [ ] Remote state backend configured (`backend.tf.example`)
- [ ] Auth0 production tenant + MFA policy
- [ ] Secrets in AWS Secrets Manager (no secrets in images)
- [ ] Database migration plan approved (run **after** infra, separate change)

## Order (target)

1. `terraform plan` → human approval → `terraform apply` (infra)
2. Push images to ECR (manual or approved workflow)
3. Register ECS task definitions (web, api, ai, worker, beat)
4. Create ECS services behind ALB with health checks (`/health`)
5. Configure DNS/TLS (ACM certificate on ALB)
6. Smoke test with test org — **not** public launch

## Rollback

See [ROLLBACK_PLAN.md](./ROLLBACK_PLAN.md).

## Explicit non-actions (F7.6)

- No `terraform apply` from CI
- No automatic deploy on push to `develop`
