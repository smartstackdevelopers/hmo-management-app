# Monorepo architecture (F1.1)

HMore is a single repository with one FastAPI backend for web, iOS and Android. AI is a separate service.

## Tree

```text
apps/web            Next.js 15 + TypeScript + Tailwind CSS
apps/mobile         Pointer to the current Expo app (see below)
apps/api            Python FastAPI (production API)
apps/ai-service     LangGraph foundation service
packages/contracts  Shared TypeScript health types
packages/config     Shared TypeScript compiler defaults
infra/docker        Dockerfiles and Compose
infra/ci            Notes for GitHub Actions
docs/               Plan, audit, architecture, setup
room-ready/         Existing Expo application (preserved)
api/                Existing Node/Express + SQLite API (reference only)
```

## Migration decisions

1. **Room Ready stays in `room-ready/`.** Moving it to `apps/mobile` in the same change would rewrite Expo/EAS paths before FastAPI is the client backend. CI typechecks `room-ready`. `apps/mobile/README.md` records the later move.
2. **Node `api/` stays as reference.** New HTTP traffic belongs in `apps/api`. Do not extend Express as the production API.
3. **Postgres and Redis run in Compose** so later phases have local infrastructure. F1.1 does not create a schema or connect FastAPI to Postgres.
4. **Celery is imported as a worker app** in `apps/api/app/workers/celery_app.py`. There are no business tasks yet.

## Service ports

| Service | Port |
| --- | --- |
| Web | 3000 |
| FastAPI | 8000 |
| AI service | 8001 |
| Postgres | 5432 |
| Redis | 6379 |

Web, iOS and Android will call `apps/api`. The AI service is not called from clients except through the API in later phases.
