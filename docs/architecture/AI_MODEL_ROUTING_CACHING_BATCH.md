# F3.2 — Model routing, caching, and batch jobs

Extends the F3.1 shared AI service. Future agents **must** use these shared layers — they must not hardcode provider/model selection.

## Model routing

- **Registry:** `AI_MODEL_REGISTRY_JSON` or built-in `default_low_cost` / `default_premium`.
- **Default:** low-cost model (`AI_DEFAULT_MODEL_KEY`, default `default_low_cost`).
- **Escalation:** only when policy allows (`AI_ESCALATION_*`), max attempts bounded, reasons recorded. LLM text cannot pick arbitrary models.
- **Preview:** `POST /api/v1/routing/preview`, inventory `GET /api/v1/models`.

## Caching

- Backends: `memory` (default/tests), `redis`, or `none`.
- Keys: SHA-256 of canonical payload including **organisation id**, prompt id/version, provider/model, workflow, hashed input — never raw PII in the key material beyond org UUID scoping.
- Org isolation enforced by key prefix `hmore:ai:v1:org:{uuid}:…`.
- Short locks reduce duplicate concurrent calls; lock expiry prevents deadlocks.
- Redis down: fail-open to compute path when `AI_CACHE_FAIL_OPEN=true` (default).

## Batch jobs (Celery)

- Celery app: `hmore-ai` on `REDIS_URL` (distinct from core API app name).
- Tasks: `hmore.ai.batch.execute_workflow`, scheduled `hmore.ai.batch.scheduled_foundation_ping` (infrastructure only — no tenant AI).
- Statuses: queued → running → completed|failed|cancelled.
- Idempotent submit via `idempotency_key`.
- Job status/results are organisation-scoped; job IDs cannot cross orgs.
- `AI_BATCH_EAGER=true` runs inline for tests/local without a worker.

## Usage metadata (for F3.3)

Adds cache hit, escalation flags/reason, batch job id fields. Monetary cost remains `null`.

## Out of scope

F3.3 caps/dashboard and F3.4+ agents are not implemented here.
