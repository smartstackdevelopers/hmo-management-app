# Shared AI Service architecture (F3.1)

## Boundaries

| Component | Responsibility |
|-----------|----------------|
| `apps/api` (FastAPI) | Authoritative business records, RBAC, organisation isolation, workflow decisions |
| `apps/ai-service` | Shared LangGraph workflows, prompt versions, LLM provider adapter, AI suggestions |
| Web / Mobile | Never call the AI service directly in production; go through the core API |

The AI service **must not** write important business records on its own. Important actions pause for **human approval**; applying changes remains a core-API concern in later Phase 3 features.

## OpenAPI gateway

Base URL (local): `http://127.0.0.1:8001`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | public | Liveness + LangGraph compile ping |
| GET | `/ready` | public | Readiness (token required in production) |
| GET | `/api/v1/health` | public | Versioned health |
| GET | `/api/v1/ready` | public | Versioned readiness |
| GET | `/api/v1/workflows` | S2S + feature | List registered workflows |
| POST | `/api/v1/workflows/execute` | S2S + feature | Run an allow-listed workflow |
| GET | `/api/v1/prompts` | S2S + feature | Prompt version **summaries** (no templates) |
| GET | `/api/v1/provider` | S2S | Provider configuration status (no secrets) |
| GET | `/api/v1/approvals/{id}` | S2S + feature | Approval status |
| POST | `/api/v1/approvals/{id}/decide` | S2S + feature | Explicit human approve/reject |
| GET | `/openapi.json` | public | OpenAPI document |
| GET | `/docs` | public | Swagger UI |

## Authentication and organisation context

1. Caller presents `Authorization: Bearer <AI_SERVICE_TOKEN>`.
2. Trusted context is taken **only** from headers set by the core API after it has already authenticated the user:
   - `X-HMore-Organisation-Id`
   - `X-HMore-User-Id`
   - `X-HMore-Role`
   - `X-HMore-Features` (optional; defaults from env)
   - `X-Correlation-Id`
3. `organisation_id` in a request **body is never authoritative**. Mismatch with the trusted header is rejected (`403`).

## LangGraph

- `foundation_ping` — compile/smoke graph.
- `foundation_echo` — sample controlled path: resolve published prompt → allow-listed `echo_safe` tool → optional human approval pause.

Future agents (F3.4+) register additional workflows in the same service; they do not get a separate AI backend.

## Prompt versioning

- Identifiers + immutable published versions (`draft` → `published` → `deprecated`).
- Active version resolution returns the published version only.
- F3.1 storage is **in-process memory** (seeded at startup). Multi-replica persistence is deferred; the resolution API stays stable.

## LLM providers

`LLM_PROVIDER=none|mock|openai`

- `mock` is **explicit** for tests/dev only.
- `openai` without `OPENAI_API_KEY` fails clearly — never silent fake completions.
- Token usage is recorded only when the provider returns it; monetary cost is always `null` in F3.1.

## Human approval foundation

AI output is tagged `source=ai_suggestion`. Workflows may set `requires_approval` and create a pending approval. Only an authenticated human reviewer (`X-HMore-User-Id`) can approve/reject. Approval does **not** mutate HMore business tables in F3.1.

## Usage metadata

Each execution returns usage fields suitable for F3.3 (provider, model, tokens if known, workflow, prompt version, org, duration, status). No invented costs.

## Security controls

- Shared-secret S2S auth, request size limits, timeouts, redacted logs, no arbitrary tools, no prompt template leakage via list API, no public business write path.

## How future agents use this service

1. Core API authenticates the user and checks RBAC/feature flags.
2. Core API calls `POST /api/v1/workflows/execute` with the service token and trusted headers.
3. Agent-specific LangGraph workflow runs with published prompts and allow-listed tools.
4. Model selection goes through the shared F3.2 router (low-cost default + bounded escalation).
5. Eligible responses use the shared cache; batch/overnight work uses Celery task helpers.
6. If the action is important, the workflow returns `requires_approval=true`.
7. A human decides via the approval endpoints; the core API then applies the change under normal validation.

See also: `docs/architecture/AI_MODEL_ROUTING_CACHING_BATCH.md`.
