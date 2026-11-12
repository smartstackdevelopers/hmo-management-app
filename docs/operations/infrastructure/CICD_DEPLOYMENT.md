# CI/CD deployment preparation

## Existing CI

| Workflow | Purpose |
| --- | --- |
| `.github/workflows/ci.yml` | Lint, test, build web, Playwright |
| `infra/ci/infra-validate.workflow.yml.example` | Copy to `.github/workflows/` after merge — Terraform fmt/validate, Docker builds |

## Production deploy (not wired)

Production deployment must:

1. Use `workflow_dispatch` with required reviewers (GitHub environment protection)
2. Build and scan images; push to ECR only after approval
3. Run database migrations in a controlled job (separate from F7.6)
4. Never use long-lived AWS access keys — prefer OIDC role `hmore-github-deploy`

Template workflow is **not** added as an auto-run job to avoid accidental deploy.

## Mobile

Expo EAS build/submit remains F7.7; binaries point at production API URL env at build time.
