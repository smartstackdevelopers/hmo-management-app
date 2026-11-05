# Environment and Secrets Management Guide (F1.11)

## Principles

1. Secrets never enter git.
2. Browser bundles never receive backend secrets (`NEXT_PUBLIC_*` is public).
3. Production boots fail closed when critical config is missing.
4. Prefer IAM roles over long-lived access keys.
5. Rotate and revoke secrets when staff leave or a leak is suspected.

## Inventory (Phase 1)

| Variable | Service | Required in production? | Secret? | Notes |
| --- | --- | --- | --- | --- |
| `ENVIRONMENT` | api | Yes | No | `production` enables strict validation |
| `DATABASE_URL` | api | Yes | Yes | Prefer Secrets Manager injection |
| `TEST_DATABASE_URL` | api | No | Yes | CI/local tests |
| `REDIS_URL` | api | Recommended | Yes | Auth + TLS in prod |
| `CORS_ALLOWED_ORIGINS` | api | Yes | No | Comma-separated; no `*` |
| `ENFORCE_HTTPS_ORIGINS` | api | Recommended | No | Rejects non-localhost `http://` |
| `AUTH0_DOMAIN` | api/web | Yes | No | Host only |
| `AUTH0_AUDIENCE` | api/web | Yes | No | |
| `AUTH0_ISSUER` | api | Optional | No | Derived from domain if unset |
| `AUTH0_REQUIRE_MFA_CLAIM` | api | Recommended for staff | No | |
| `AUTH0_CLIENT_ID` | web | Yes | No | Public client id |
| `AUTH0_CLIENT_SECRET` | web | Yes | **Yes** | Server only |
| `AUTH0_SECRET` | web | Yes | **Yes** | Cookie encryption |
| `APP_BASE_URL` | web | Yes | No | |
| `NEXT_PUBLIC_API_BASE_URL` | web | No | No | Public API origin |
| `STORAGE_PROVIDER` | api | Yes | No | `s3` or `local` in prod — not `memory` |
| `S3_BUCKET` / `S3_REGION` | api | If s3 | No | |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | api | Optional | **Yes** | Omit when using IAM |
| `S3_ENDPOINT_URL` | api | Optional | No | MinIO/local only |
| `OPENAI_API_KEY` | ai | Later | **Yes** | Unused in Phase 1 agents |

## Safe local setup

1. Copy `apps/api/.env.example` → `apps/api/.env` (gitignored).
2. Copy `apps/web/.env.example` → `apps/web/.env.local`.
3. Never paste production secrets into examples or chat logs.
4. Use `openssl rand -hex 32` for local `AUTH0_SECRET` placeholders.

## Production secret storage (target)

| Secret class | Target store | Access |
| --- | --- | --- |
| DB credentials | AWS Secrets Manager | Task role only |
| Auth0 client secret / cookie secret | Secrets Manager | Web/API task roles |
| S3 | Prefer IAM role; else Secrets Manager | Least privilege bucket policy |
| KMS CMKs | AWS KMS | Encrypt/decrypt via roles; no plaintext key export |

**Status:** Documented target. No AWS resources created by this feature.

## Rotation and revocation

1. Rotate DB password in Secrets Manager; rolling restart API tasks.
2. Rotate Auth0 client secret in Auth0 + Secrets Manager together.
3. Disable compromised IAM users/keys immediately; prefer roles so keys are rare.
4. Revoke Auth0 sessions/users on staff offboarding.
5. Record rotation in the organisation’s change log (process — not automated in Phase 1).

## Logging redaction

Use `app.core.secrets.redact_mapping` / `redact_database_url` before writing diagnostics. Never log Authorization headers, cookies, or raw `DATABASE_URL` passwords.

## Development vs production

| | Development | Production |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | `production` |
| Missing Auth0 | Allowed (features degrade) | Boot fails |
| Storage `memory` | Allowed | Rejected |
| OpenAPI `/docs` | Enabled | Disabled |
| CORS `*` | Discouraged | Rejected |
