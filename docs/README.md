# HMore docs

This folder is the working contract for HMore.

**Source of truth:** [HMore Proposal-Exact Complete Implementation Plan v1.0](./HMore-Proposal-Exact-Implementation-Plan-v1.0.md)

Aligned 1:1 to Smart Vite Project Proposal v1.3. Product name in delivery is **HMore**. Optional add-ons in Section 11 stay optional.

## How we work

1. Implement only the phase that is currently in progress.
2. Finish that phase exit checklist before starting the next phase.
3. Do not drop, weaken, or replace any core proposal requirement.
4. Current `room-ready` (Expo) and `api` (Node/Prisma) are reference only. The production stack is Next.js, Expo, Python FastAPI, PostgreSQL + pgvector, LangGraph, Celery + Redis, private S3, AWS UK/EU.

**Start here:** Phase 1 — Foundation. F1.1 monorepo: [MONOREPO_ARCHITECTURE.md](./architecture/MONOREPO_ARCHITECTURE.md). F1.2 database: [DATABASE_ARCHITECTURE.md](./architecture/DATABASE_ARCHITECTURE.md). F1.3 Auth0 identity: [IDENTITY_ARCHITECTURE.md](./architecture/IDENTITY_ARCHITECTURE.md). F1.4 RBAC: [RBAC_ARCHITECTURE.md](./architecture/RBAC_ARCHITECTURE.md). F1.5 organisation isolation: [ORGANISATION_ISOLATION_ARCHITECTURE.md](./architecture/ORGANISATION_ISOLATION_ARCHITECTURE.md). Local commands: [LOCAL_SETUP.md](./development/LOCAL_SETUP.md). Branch family: `feature/phase1-*` / `chore/phase1-*`.

Original PDF: [HMore_Proposal_Exact_Implementation_Plan_v1.0.pdf](./HMore_Proposal_Exact_Implementation_Plan_v1.0.pdf)

## Prototype to build

The clickable prototype must match the Smart Vite screen pack. Agents building UI follow this document, not a redesigned layout.

- Agent spec: [Smart Vite Prototype](./Smart-Vite-Prototype.md)
- Original screens (50 pages): [Smart Vite Prototype Complete.pdf](./Smart-Vite-Prototype-Complete.pdf)

The prototype brand on screen is **Smart Vite**. The delivery product name in the implementation plan is **HMore**. Keep the drawn screens, copy, sample data, and six roles. Do not add a seventh role or extra modules.
