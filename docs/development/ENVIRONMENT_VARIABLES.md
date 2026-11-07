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
| `AUTH0_DOMAIN` | api, web | Auth0 tenant host without scheme | Required for live auth |
| `AUTH0_AUDIENCE` | api, web, mobile | API identifier | Required for API access tokens |
| `AUTH0_ISSUER` | api | Token issuer (`https://{domain}/`) | Optional; derived from domain |
| `AUTH0_REQUIRE_MFA_CLAIM` | api | Require `amr` contains `mfa` | Optional, default false |
| `STORAGE_PROVIDER` | api | `memory` / `local` / `s3` private file backend | No, default `memory` |
| `STORAGE_LOCAL_ROOT` | api | Local private disk root | No |
| `STORAGE_MAX_UPLOAD_BYTES` | api | Upload size cap | No |
| `STORAGE_ALLOWED_CONTENT_TYPES` | api | MIME allow-list | No |
| `S3_*` | api | Endpoint, region, bucket, keys, path-style | Required when provider=`s3` |
| `AUTH0_CLIENT_ID` / `AUTH0_CLIENT_SECRET` | web | Regular Web Application | Required for web login |
| `AUTH0_SECRET` | web | Session cookie encryption | Required for web login |
| `APP_BASE_URL` | web | App origin, e.g. `http://localhost:3000` | Required for web login |
| `EXPO_PUBLIC_AUTH0_*` | mobile | Native app public config | Required for Expo Auth0 |
| `EMAIL_ADAPTER_MODE` | api | `test` (default, no network) or `smtp` | No |
| `SMTP_HOST` | api | SMTP server hostname | When using SMTP |
| `SMTP_PORT` | api | SMTP port (default 587) | When using SMTP |
| `SMTP_USER` / `SMTP_PASSWORD` | api | SMTP auth (optional if IAM/relay) | When required |
| `SMTP_FROM_EMAIL` | api | Envelope From for operational email | When using SMTP |
| `SMS_ADAPTER_MODE` | api | `test` (default) or `twilio` | No |
| `TWILIO_ACCOUNT_SID` | api | Twilio account SID | When `SMS_ADAPTER_MODE=twilio` |
| `TWILIO_AUTH_TOKEN` | api | Twilio auth token | When `SMS_ADAPTER_MODE=twilio` |
| `TWILIO_FROM_NUMBER` | api | Twilio sender number | When `SMS_ADAPTER_MODE=twilio` |

The Node `api/` still reads `JWT_SECRET` and `DATABASE_URL` for Room Ready. That is the reference API. Do not copy its development JWT fallback into FastAPI.
