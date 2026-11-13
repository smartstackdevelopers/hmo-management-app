# Deployment and rollback guide

Production deploy **requires authorised approval** — no automatic deploy from `develop` (F7.6 CI/CD policy).

## Release preparation

1. Merge feature branch to `develop`; CI green on GitHub Actions.
2. Tag release candidate **PENDING APPROVAL** versioning scheme.
3. Review Alembic migrations in release — separate approval from infra change.
4. Update change record **CONFIG_PLACEHOLDER**.

## Build verification

| Artifact | Check |
| --- | --- |
| API image | Unit tests; Alembic head matches release notes |
| Web image | `npm run build`; e2e smoke **PENDING APPROVAL** in staging |
| AI image | `test_health` |
| Worker image | `Dockerfile.worker` builds |
| Mobile | EAS build profile `production` — separate F7.7 process |

## Environment checks (pre-deploy)

- Secrets in Secrets Manager — not in image.
- `AUTH0_REQUIRE_MFA_CLAIM=true` for production staff **PENDING APPROVAL**.
- `SENTRY_DSN` scrubbing rules **PENDING APPROVAL**.
- Backup enabled if policy requires `BACKUP_ENABLED=true`.

## Database migration checks

1. Fresh backup with verification **passed**.
2. Run `alembic upgrade head` on staging clone first.
3. Maintenance window for breaking migrations **PENDING APPROVAL**.

**Never** recommend automatic destructive rollback of applied migrations on production.

## Deployment approval

Sign-off: **CONFIG_PLACEHOLDER — Release manager** + **CONFIG_PLACEHOLDER — Client** when required.

## Deploy steps (target ECS)

Consolidated from `docs/operations/infrastructure/DEPLOYMENT_RUNBOOK.md`:

1. Push images to ECR.
2. Update task definitions (web → api → ai → worker → beat order **PENDING APPROVAL**).
3. Rolling update ECS services.
4. Run migrations via one-off task **after** API image available.
5. Smoke tests (health, login test org).

## Health verification

- `GET /health` on API and AI through ALB.
- Web `/health`.
- Critical dashboard paths for test org.

## Post-deployment monitoring

- Sentry error rate 30–60 minutes **PENDING APPROVAL** window.
- Backup job success.
- Celery queue depth normal.

## Rollback decision

Rollback **application image** when:

- New code causes 5xx or auth regression.
- No irreversible migration applied.

Do **not** rollback DB schema automatically — restore from backup instead with approval.

## Rollback procedure

See `docs/operations/infrastructure/ROLLBACK_PLAN.md`:

1. Revert ECS task to previous image digest.
2. Verify `/health` and Auth0 login.
3. Document incident.

## Post-rollback testing

- Repeat smoke tests.
- Confirm Alembic revision compatible with rolled-back code (migrations must be backward compatible or not yet applied).

## Local / docker-compose

`infra/docker/docker-compose.prod.example.yml` — healthcheck hits `http://127.0.0.1:8000/health`.
