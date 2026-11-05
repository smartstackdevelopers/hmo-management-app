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

## Docker

```text
docker compose -f infra/docker/docker-compose.yml up --build
```

Postgres is included for later schema work. FastAPI does not migrate or query it in F1.1.

## Known limitations

- Python and Node must be installed on the machine. Windows Store Python stubs will fail.
- Docker is optional. Compose was not required to prove FastAPI or Next.js locally.
- The Expo app still talks to the Node API in `api/` until later phases switch the client to FastAPI.
