# Target architecture

Source: HMore Proposal-Exact Complete Implementation Plan v1.0, Section 1 and Section 8. This file describes the required end state. It does not describe the current repository as already matching that state.

## Required production stack

| Layer | Required | In this repository today |
| --- | --- | --- |
| Web dashboard | Next.js + TypeScript + Tailwind CSS | Not present. Expo can start a web bundle. |
| Mobile | React Native + Expo | Present as `room-ready/`, branded Room Ready. |
| Backend API | Python + FastAPI, REST + OpenAPI | Not present. Node + Express exists as reference. |
| Database | PostgreSQL + pgvector | Not present. Prisma uses SQLite. |
| AI | LangGraph, tiered LLM, usage caps, separate service | Not present. `room-ready/lib/ai.ts` is local keyword logic. |
| Identity | Auth0 or Entra External ID, with MFA | Not present. Local bcrypt + JWT. |
| Jobs | Celery + Redis | Not present. |
| Files | Private S3-compatible storage | Local disk, publicly served under `/uploads`. |
| Cloud | AWS, UK or EU region | Not configured. |
| Quality | GitHub Actions, Pytest, Playwright | Not configured. |
| Monitoring | Sentry or equivalent | Not configured. |

One shared backend serves web, iOS, and Android. AI is a separate service behind a controlled gateway. Exactly six roles. Organisation data isolation is mandatory. Important AI actions need human approval.

## Target tree

```text
hmore/
  apps/web
  apps/mobile
  apps/api
  apps/ai-service
  packages/shared-contracts
  infra/docker
  infra/aws
  infra/ci
  docs/architecture
  docs/security
  docs/database
  docs/api
  docs/development
  docs/audit
```

## Current tree

```text
room-ready/    Expo app
api/           Node + Prisma + SQLite
docs/          Plan, prototype spec, audit
```

## Migration requirements

Do not rename or move `room-ready` or `api` until a reviewed chore branch does it.

1. Add the target folders beside the current apps. Leave `room-ready` and `api` in place until FastAPI covers the same behaviour that must be kept.
2. Treat `api/` as a behaviour reference. Do not extend it as the production API.
3. Design the PostgreSQL schema for Phase 1 entities: organisation, membership, the six roles, user identity link, tenant, property, room, audit event, emergency access, file metadata. Do not point Prisma SQLite migrations at production.
4. Put the Expo app behind `apps/mobile` only after import paths, EAS config, and CI are updated together.
5. Add `apps/web` as a new Next.js shell. Do not treat Expo web as that shell.
6. Add `apps/ai-service` empty of business agents until Phase 3. Phase 1 only needs the boundary documented, not the agents built.
7. Add `packages/shared-contracts` when the first FastAPI schemas exist, so web and mobile do not duplicate types by hand.
8. Add `infra/` for Docker Compose (Postgres, Redis), the GitHub Actions workflow, and an AWS UK/EU baseline note. No production deploy in Phase 1.

## Risks

- Moving Expo now breaks the only runnable client before the new API exists.
- Copying the SQLite schema into Postgres would lock in the wrong roles and the missing organisation boundary.
- Keeping two backends alive without a written cut-over will split business rules.
- The prototype screens use the name Smart Vite. The delivery name is HMore. UI rename is a product decision, not an architecture substitute.
- Room occupancy cameras stay gated by the Phase 1 survey and a later DPIA. No camera build in the migration.
