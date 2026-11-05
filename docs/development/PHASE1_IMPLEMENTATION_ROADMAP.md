# Phase 1 implementation roadmap

Phase 1 is Foundation. Do not start these items until `develop` contains `main` and work happens on `feature/phase1-*` or `chore/phase1-*` branches with pull requests into `develop`.

Exit checks from the plan, none of which pass today:

- MFA login works for staff and admin paths.
- All six roles exist and are enforceable.
- Organisation data separation is proven by deny tests.
- Tenant and property records can be created with audit entries.
- CI is green.
- Occupancy feasibility survey template is ready for the client.

## Order

The order is dependency order, not a time estimate.

### 1. Governance and repo shape — F1.1

- Fast-forward `develop` to `main` under the procedure in `docs/development/GIT_WORKFLOW.md`.
- Add `apps/web`, `apps/api`, `apps/ai-service`, `packages/shared-contracts`, and `infra/` without moving `room-ready` or `api` in the same change.
- Add a GitHub Actions workflow that runs on pull requests to `develop`: format, lint, typecheck, and a job that fails if secrets files are committed. Pytest and Playwright jobs start as soon as those projects exist. Until they exist, the workflow must not pretend those tests ran.
- Keep Node `api/` out of the production build.

### 2. Data model — F1.2, F1.5, F1.6, F1.7

- New PostgreSQL database. Do not migrate the SQLite file forward as the production schema.
- Tables for organisation, membership, the six roles, tenant, property, room, audit event, and emergency access.
- Row access always includes `organisation_id` except for Super Admin platform operations, which are still written to the audit log.
- Alembic or an equivalent FastAPI migration tool. Prisma SQLite migrations stay with the reference API.

### 3. Identity — F1.3, F1.4

- Auth0 or Entra External ID. The choice is a human decision recorded before coding.
- MFA required on staff and admin paths.
- Map tokens to the six roles. Do not keep `property_manager` or the current `admin` role as core roles.
- Session timeout and revocation. The current 30-day local JWT is not the design.

### 4. API baseline — F1.6, F1.7, F1.8

- FastAPI routes for organisation membership, tenant, property, and room.
- Deny tests for cross-organisation reads and writes.
- Audit entry on create and update.
- File metadata API that stores bytes in private S3-compatible storage. No public `/uploads` equivalent.

### 5. Web shell — F1.9

- New Next.js app with Tailwind.
- Sign-in handoff to the identity provider.
- Empty home shells for Super Admin, Organisation Admin, and Landlord.
- Mobile remains Expo. Landlord and admin day-to-day work stays on the web, as the plan requires.

### 6. Security and occupancy paperwork — F1.10, F1.11

- Document encryption in transit (TLS) and at rest (database and S3), secret storage, and the AWS UK/EU account layout. This is a baseline document plus repo config, not a production cut-over.
- Write the occupancy site-survey checklist. Do not integrate cameras.

## Explicitly out of Phase 1

Support plans, repairs workflow beyond the baseline records needed later, AI agents, push notifications, community services, finance, and room-occupancy counting. The existing Express routes for those areas stay untouched as reference.

## Quality bar for every Phase 1 pull request

- Typed schemas, validated input, and consistent error responses.
- Tests for allow and deny.
- No hardcoded secrets and no fallback signing key.
- No placeholder success responses.
- No new primary framework besides the stack in the plan.
