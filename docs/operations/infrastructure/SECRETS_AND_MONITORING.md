# Secrets and monitoring

## Secrets (production)

| Secret | Store | Consumed by |
| --- | --- | --- |
| `DATABASE_URL` | Secrets Manager | API, workers |
| `REDIS_URL` | Secrets Manager | API, AI, workers |
| Auth0 client secret / cookie secret | Secrets Manager | Web |
| `AI_SERVICE_TOKEN` | Secrets Manager | API ↔ AI |
| `OPENAI_API_KEY` | Secrets Manager | AI service |
| `INTEGRATION_SECRETS_KEY` | Secrets Manager | API |
| S3 access | **IAM task role** (preferred) | API |

Never commit production values. See `docs/security/ENVIRONMENT_AND_SECRETS_GUIDE.md`.

## Sentry

- API: `app/core/sentry.py` — activates when `SENTRY_DSN` set (`send_default_pii=False`)
- AI: same pattern
- Web: optional `SENTRY_DSN` / client DSN only if approved
- Filter tenant names, free-text notes, and document titles in custom scrubbers before go-live

## CloudWatch

Log groups prepared in Terraform module `observability` (when `stack_enabled`).

## Alerts (pending)

- ALB 5xx rate
- ECS task health
- RDS CPU / storage
- Redis evictions
- Celery queue depth (custom metric)
