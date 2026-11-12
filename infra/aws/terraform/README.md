# HMore AWS Terraform (F7.6)

**Status:** Prepared definitions only. **Default `stack_enabled = false` creates zero AWS resources.**

## Region

- **Preferred:** `eu-west-2` (London) for UK hosting — **PENDING APPROVAL**
- Alternative: `eu-west-1` (Ireland) — document cross-border transfers if selected

## Commands (local / CI — no apply)

```bash
cd infra/aws/terraform/environments/production
terraform fmt -check -recursive ../../..
terraform init -backend=false
terraform validate
terraform plan   # requires AWS credentials; expect 0 changes when stack_enabled=false
```

## Apply gate

1. Client approves region, account, and cost.
2. Set `stack_enabled = true` in approved `terraform.tfvars`.
3. Configure remote backend (`backend.tf.example`).
4. Run `terraform plan` in change window; require human approval before `terraform apply`.
5. **Do not** run `terraform apply` from CI.

See `docs/operations/infrastructure/` and `docs/phase7/F7.6_INFRASTRUCTURE_FINAL_REPORT.md`.
