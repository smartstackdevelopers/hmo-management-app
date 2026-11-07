# AI service — local development (F3.1)

## Run

```text
cd apps/ai-service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Set AI_SERVICE_TOKEN to a long random string
uvicorn app.main:app --reload --port 8001
```

- Health: http://127.0.0.1:8001/health  
- OpenAPI: http://127.0.0.1:8001/docs  

## Docker

```text
docker compose -f infra/docker/docker-compose.yml up --build ai
```

Compose sets `ENVIRONMENT=development`. Set `AI_SERVICE_TOKEN` in the compose environment for protected route testing.

## Tests

```text
cd apps/ai-service
pytest -q
```

- Default suite uses `LLM_PROVIDER=mock` + in-memory cache + eager batch.
- Real OpenAI: `@pytest.mark.real_llm` (skips without a real key — skips are not passes).
- Real Redis: `@pytest.mark.real_redis` with `REDIS_URL_REAL`.

## Celery worker (optional local)

```text
cd apps/ai-service
celery -A app.batch.celery_app.celery_app worker -l info
celery -A app.batch.celery_app.celery_app beat -l info
```

Set `AI_BATCH_EAGER=false` to require a live worker.

## Calling a protected endpoint

```text
curl -X POST http://127.0.0.1:8001/api/v1/workflows/execute ^
  -H "Authorization: Bearer <AI_SERVICE_TOKEN>" ^
  -H "X-HMore-Organisation-Id: 11111111-1111-1111-1111-111111111111" ^
  -H "X-HMore-User-Id: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" ^
  -H "X-HMore-Role: organisation_admin" ^
  -H "Content-Type: application/json" ^
  -d "{\"workflow_id\":\"foundation_echo\",\"message\":\"hello\"}"
```

## Production notes (not deployed in F3.1)

- Run in AWS UK/EU private network; do not expose the AI service publicly.
- Inject `AI_SERVICE_TOKEN` and provider keys via Secrets Manager.
- Terminate TLS at the load balancer / service mesh.
- Prefer shared prompt persistence before multi-replica scale-out.
