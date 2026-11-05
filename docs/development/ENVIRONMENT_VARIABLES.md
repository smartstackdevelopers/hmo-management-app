# Environment variables

Never commit real secrets. Track `*.env.example` only.

| Variable | Service | Purpose | Required |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_APP_NAME` | web | Display name | No, has a default in copy |
| `NEXT_PUBLIC_API_BASE_URL` | web | FastAPI origin for later client calls | No for the health page |
| `APP_NAME` | api, ai | OpenAPI title | No |
| `ENVIRONMENT` | api, ai | `development` / `test` / `production` | No |
| `API_V1_PREFIX` | api, ai | Defaults to `/api/v1` | No |
| `LOG_LEVEL` | api | Reserved for structured logging | No |
| `REDIS_URL` | api | Celery broker | Only if a worker is started |
| `DATABASE_URL` | api | PostgreSQL URL for Alembic and the ORM (`postgresql+psycopg://...`) | Yes for migrations and schema tests |
| `TEST_DATABASE_URL` | api | Isolated DB for Pytest | Recommended locally; set in CI |
| `OPENAI_API_KEY` | ai | Unused by the foundation graph | Leave empty |
| `POSTGRES_*` | compose | Local Postgres bootstrap | Only for Compose |

The Node `api/` still reads `JWT_SECRET` and `DATABASE_URL` for Room Ready. That is the reference API. Do not copy its development JWT fallback into FastAPI.
