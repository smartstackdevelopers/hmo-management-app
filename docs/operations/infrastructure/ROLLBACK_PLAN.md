# Infrastructure rollback plan

## Application (ECS)

1. Identify last known-good task definition revision
2. Update ECS service to previous revision (rolling deploy)
3. Verify `/health` and Auth0 login smoke test

## Database

- Do **not** roll back schema by deleting RDS
- Forward-fix migrations preferred; restore from snapshot only with written approval (RPO/RTO)

## Terraform

- Revert to previous git tag of `infra/aws/terraform`
- `terraform plan` showing destruction requires explicit approval
- `stack_enabled` can be set `false` to plan teardown — still requires approval

## Secrets

- If leak suspected: rotate in Secrets Manager + Auth0, restart tasks
