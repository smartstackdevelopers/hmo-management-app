# Full authentication onboarding (Auth0 + 6 roles)

Use this checklist on branch `feature/full-auth-onboarding` before staging/production deploy.
Legacy Room Ready login (port **3001**) is **not** HMore — use Auth0 only for deploy.

## Roles (exactly 6)

| Code | Who |
| --- | --- |
| `super_admin` | Platform operator (no organisation) |
| `organisation_admin` | One organisation |
| `landlord` | One organisation |
| `tenant` | One organisation |
| `support_worker` | One organisation |
| `maintenance_contractor` | One organisation |

List in CLI: `python scripts/bootstrap_identity.py list-roles` (from `apps/api`).

## 1. Infrastructure

1. PostgreSQL (Docker): `docker compose -f infra/docker/docker-compose.yml up -d postgres`
2. Migrate: `cd apps/api && alembic upgrade head`
3. Auth0 UK/EU tenant per `IDENTITY_PROVIDER_SETUP.md`:
   - API (audience `https://api.hmore.local` or production URI)
   - Regular Web App → web env
   - Native App → `room-ready` env (`EXPO_PUBLIC_AUTH0_*`)

## 2. Environment files (never commit secrets)

| App | File |
| --- | --- |
| API | `apps/api/.env` — `DATABASE_URL`, `AUTH0_*` |
| Web | `apps/web/.env.local` — `AUTH0_*`, `APP_BASE_URL` |
| Mobile | `room-ready/.env` — `EXPO_PUBLIC_AUTH0_*`, `EXPO_PUBLIC_HMORE_API_URL` |

Mobile API URL on a physical device must use the PC LAN IP, e.g. `http://192.168.1.10:8000/api/v1`.

Remove or leave unset `EXPO_PUBLIC_API_URL` so the app does not use legacy port 3001.

## 3. Create Auth0 users

In Auth0 Dashboard, create users (or enable sign-up policy) with **the same email** you will bootstrap in HMore.

Staff paths should use MFA per `MFA_CONFIGURATION.md`.

## 4. Bootstrap roles in HMore (before or after first login)

From `apps/api` with venv active:

```text
python scripts/bootstrap_identity.py grant-super-admin --email platform-admin@yourorg.example
python scripts/bootstrap_identity.py grant-org-role --email oa@yourorg.example --role organisation_admin --org-slug demo-housing --org-name "Demo Housing"
python scripts/bootstrap_identity.py grant-org-role --email tenant@yourorg.example --role tenant --org-slug demo-housing
python scripts/bootstrap_identity.py show-user --email platform-admin@yourorg.example
```

Production/staging: set `ENVIRONMENT=production` and `HMORE_BOOTSTRAP_TOKEN`, then pass `--token` on each command. Remove or rotate the token after onboarding.

First login links Auth0 `sub` to the existing row via email (`app/auth/identity.py`).

## 5. Smoke tests

| Client | Step | Expected |
| --- | --- | --- |
| Web | `http://localhost:3000/auth/login` | Auth0 login → `/account` |
| API | Bearer token → `GET /api/v1/auth/me` | 200, `external_subject` set |
| API | `GET /api/v1/rbac/me` | Active role + organisation |
| Mobile | Auth0 login | Tabs match role; API calls to `/api/v1` |

Automated token rules: `pytest -q tests/test_auth_tokens.py`  
PostgreSQL bootstrap: `pytest -q tests/test_identity_bootstrap.py`

## 6. Deploy notes

- All three clients must share the same `AUTH0_AUDIENCE` / API identifier.
- Production callbacks and mobile redirects must be added in Auth0 (not only localhost).
- Do not run legacy `api/` (3001) in production for HMore.
- Super Admin is assigned only via bootstrap or an existing Super Admin (`assign_membership` API).

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| 403 / no active role | Run `show-user`; add membership with bootstrap CLI |
| Email claim missing | Auth0 Action to add `email` to access token |
| Mobile Failed to fetch | Wrong `EXPO_PUBLIC_HMORE_API_URL` or API not reachable |
| Legacy demo login | Unset Auth0 mobile env; legacy is for UI demo only |