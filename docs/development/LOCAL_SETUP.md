# Local setup

Requires Node.js 20+, Python 3.12, and (optional) Docker.

## Install

From the repository root:

```text
npm ci
python -m venv .venv
.venv\Scripts\activate
pip install -r apps/api/requirements.txt
pip install -r apps/ai-service/requirements.txt
```

Copy `.env.example` files. Do not commit a filled `.env`.

## Run services

API:

```text
cd apps/api
uvicorn app.main:app --reload --port 8000
```

OpenAPI: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/health and http://127.0.0.1:8000/api/v1/health

AI service:

```text
cd apps/ai-service
uvicorn app.main:app --reload --port 8001
```

Health: http://127.0.0.1:8001/health

Web:

```text
npm run web:dev
```

http://127.0.0.1:3000 and http://127.0.0.1:3000/health

Mobile (existing Expo app):

```text
cd room-ready
npx expo start
```

## Tests

```text
cd apps/api && pytest -q
cd apps/ai-service && pytest -q
npm run web:typecheck
npm run web:lint
npm run web:build
npm run web:test:e2e
npm run mobile:typecheck
```

Playwright starts the Next.js app itself.

## Auth0 (F1.3)

1. Create a **UK** (preferred) or **EU** Auth0 tenant.
2. Follow `docs/development/IDENTITY_PROVIDER_SETUP.md`, `docs/development/MFA_CONFIGURATION.md`, and **`docs/development/FULL_AUTH_ONBOARDING.md`** (roles + bootstrap CLI).
3. Copy env examples for `apps/api`, `apps/web`, and `room-ready`. Never commit secrets.
4. Web login routes: `/auth/login`, `/auth/logout`, `/account`.
5. Until a real tenant is used, treat MFA and live login as unverified.

## Database (F1.2)

Start Postgres with pgvector, then migrate:

```text
docker compose -f infra/docker/docker-compose.yml up -d postgres
cd apps/api
alembic upgrade head
pytest -q
```

Details: `docs/development/DATABASE_SETUP.md` and `docs/development/DATABASE_MIGRATIONS.md`.

## Docker

```text
docker compose -f infra/docker/docker-compose.yml up --build
```

Postgres uses the `pgvector/pgvector:pg16` image. The API container receives `DATABASE_URL` pointing at that service.

## Known limitations

- Python and Node must be installed on the machine. Windows Store Python stubs will fail.
- Docker is optional. Compose was not required to prove FastAPI or Next.js locally.
- The Expo app still talks to the Node API in `api/` until later phases switch the client to FastAPI.
