# Database architecture (F1.2)

Source of truth: HMore Proposal-Exact Complete Implementation Plan v1.0, `TARGET_ARCHITECTURE.md`, and `PHASE1_IMPLEMENTATION_ROADMAP.md`.

## Purpose

PostgreSQL is the system of record for the shared FastAPI backend used by web, iOS, and Android. F1.2 delivers the Phase 1 schema and Alembic migrations only. It does not enforce organisation isolation (F1.5), permissions (F1.4), CRUD APIs (F1.6), or audit writers (F1.7).

## Technology

| Concern | Choice |
| --- | --- |
| Engine | PostgreSQL 16+ |
| Extension | `vector` (pgvector) created in the initial migration; no embedding tables yet |
| ORM | SQLAlchemy 2.0 (sync sessions; matches the sync FastAPI app) |
| Migrations | Alembic |
| Keys | UUID primary keys on every Phase 1 table |

### UUID rationale

UUID primary keys avoid leaking sequential counts across organisations, keep identifiers stable when data is merged or replicated later, and match the identity-provider subject model without requiring a central integer allocator. Values are generated in the application with `uuid4` unless a caller supplies an id in tests.

## Package layout

```text
apps/api/app/db/
  base.py          Declarative Base
  session.py       Engine and session helpers
  models/          Domain tables and enums
apps/api/migrations/  Migration environment and versions (Alembic; `alembic.ini` sets `script_location = migrations`)
```

The Node `api/` Prisma SQLite schema remains reference only and is not migrated forward.

## Naming

- Tables: plural `snake_case` (`organisation_memberships`)
- Columns: `snake_case`
- British spelling: `organisation`, not `organization`
- Enums: PostgreSQL native enums `hmore_role`, `membership_status`, `record_status`

## Multi-tenancy readiness (not enforcement)

- Org-owned tables carry a required `organisation_id` foreign key.
- `organisation_memberships` binds a user to an organisation and one of the six roles.
- Super Admin memberships use `organisation_id IS NULL` and role `super_admin`.
- `audit_events.organisation_id` is nullable so platform-wide Super Admin actions can be stored.
- Row-Level Security and request-scoped isolation are implemented in F1.5 (`docs/architecture/ORGANISATION_ISOLATION_ARCHITECTURE.md`).

## Soft deletion

Not used in F1.2. The proposal does not require soft delete for these foundation tables. Archive-style state uses `record_status` (`active` / `archived`) where a durable status is useful. Deletes should be rare and accompanied later by audit events (F1.7).

## Indexing strategy

- Every `organisation_id` column is indexed for later isolation filters.
- Unique indexes on `organisations.slug`, `users.email`, `users.external_subject`, `file_metadata.storage_key`, and `(property_id, label)` on rooms.
- Membership lookup indexes on `user_id`, `(organisation_id, role)`, and a partial unique index ensuring one Super Admin membership per user.
- Audit query indexes on `action` and `created_at`.

## Out of schema scope for F1.2

Identified from the proposal inventory but deferred by the Phase 1 roadmap (not tables in this migration):

- Support plans, housing applications, waiting lists
- Maintenance/complaint case tables and contractor work-order workflow
- Communication threads, notifications, announcements
- Room occupancy count streams and camera metadata
- Jobs/skills, community services, wellbeing content

Staff access is modelled as memberships with `support_worker` or `maintenance_contractor`, not a separate staff table.

## Security notes

- No passwords or secrets in the schema. Identity federation is F1.3 (`external_subject`).
- `DATABASE_URL` comes from the environment. Example values in `.env.example` are local Compose credentials only.
- Do not connect FastAPI to the Room Ready SQLite file.
