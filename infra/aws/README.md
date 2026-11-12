# AWS infrastructure (F7.6 prepared)

Terraform modules live under `infra/aws/terraform/`. Default configuration **does not create resources** (`stack_enabled = false`).

Do not `terraform apply` without:

1. Client approval of region (`eu-west-2` preferred), account, and cost.
2. Valid AWS credentials or GitHub OIDC deploy role.
3. Explicit production change authorisation and rollback owner.

See:

- `infra/aws/terraform/README.md`
- `docs/architecture/AWS_UK_EU_TARGET_ARCHITECTURE.md`
- `docs/operations/infrastructure/`
- `docs/phase7/F7.6_INFRASTRUCTURE_FINAL_REPORT.md`
