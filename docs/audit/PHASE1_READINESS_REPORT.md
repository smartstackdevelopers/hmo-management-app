# Phase 1 readiness report

Assessment date: 2026-11-05. Readiness: **not ready to implement Phase 1 features**. Governance is blocked until `develop` is fast-forwarded to `main`. No Phase 1 deliverable is verified.

Status values used: NOT STARTED, PARTIALLY IMPLEMENTED, IMPLEMENTED BUT UNVERIFIED, VERIFIED. Nothing is VERIFIED. GitHub Actions on commit `e67678a` succeeded for Web, Mobile typecheck, API, and AI (pull request run [42000186838](https://github.com/smartstackdevelopers/hmo-management-app/actions/runs/42000186838) and push run [42000129576](https://github.com/smartstackdevelopers/hmo-management-app/actions/runs/42000129576)). Docker Compose and the Expo runtime were not executed, so those checks stay unverified.

## Coverage matrix

| ID | Requirement | Status | Existing files | Missing work | Dependencies | Risks | Approach | Acceptance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1.1 | Monorepo + CI/CD | IMPLEMENTED BUT UNVERIFIED | `apps/web`, `apps/api`, `apps/ai-service`, `apps/mobile/README.md`, `packages/*`, `infra/docker`, `.github/workflows/ci.yml`, `room-ready/` preserved | Docker Compose has not been built or started. Expo runtime (`expo start`) has not been run. Room Ready stays in `room-ready/`. | None | Actions on `e67678a` are green for lint, typecheck, build, Playwright, API Pytest, AI Pytest, and Room Ready typecheck. Compose and Expo startup remain unverified. | Keep Room Ready in place; add FastAPI and Next.js beside it | Those GitHub checks passed on PR #2. Compose and Expo runtime are still unverified, so this row is not VERIFIED. |
| F1.2 | PostgreSQL schema + migrations | IMPLEMENTED BUT UNVERIFIED | `apps/api/app/db/*`, `apps/api/alembic/versions/20261105_1200_f12_initial_phase1_schema.py`, database docs | Local Docker/pgvector may still be unavailable on a given machine; CI must show green API+Postgres checks on the F1.2 PR | F1.1 merged | Claiming VERIFIED without a PostgreSQL migration run | SQLAlchemy + Alembic in FastAPI. Prisma SQLite stays reference | Migration upgrades/downgrades on pgvector Postgres; schema Pytest passes; health tests still pass |
| F1.3 | Managed identity + MFA | IMPLEMENTED BUT UNVERIFIED | Auth0 selected; `apps/api/app/auth/*`, web Auth0 SDK, `room-ready/lib/hmoreAuth0.ts`, identity docs | Real UK/EU Auth0 tenant login + MFA challenge not run in this environment | Human Auth0 approval recorded | Claiming verified MFA without a real tenant | Auth0 only; provider MFA; mocked JWKS tests in CI | Live staff MFA and `/auth/me` against a real tenant |
| F1.4 | Six roles, permissions, sessions | IMPLEMENTED BUT UNVERIFIED | FastAPI `app/rbac/*`, `/api/v1/rbac`, `users.authorization_version`, web `lib/rbac.ts`, RBAC docs | Live Auth0 + multi-role manual probe in a real tenant; F1.5 still owns full org isolation | F1.3 | Claiming F1.5 isolation complete; trusting UI gates | Code registry + membership-backed deps; Auth0 session docs | Deny tests fail closed; assignment cannot self-escalate; CI Pytest green |
| F1.5 | Organisation isolation + membership | IMPLEMENTED BUT UNVERIFIED | `app/tenancy/*`, isolation probes, FORCE RLS migration, org membership APIs, docs | Live multi-org Auth0 probe; CI Postgres green on F1.5 PR | F1.2, F1.4 | Forgetting org deps on new endpoints | App filters + SET LOCAL RLS; Super Admin platform path explicit | Org A cannot read/update/delete Org B; inactive membership denied |
| F1.6 | Tenant and property/room CRUD | IMPLEMENTED BUT UNVERIFIED | FastAPI `/api/v1/tenants|properties|rooms`, `app/records/*`, web foundations, F1.6 docs | Live Auth0 UI forms (F1.9); full F1.7 audit framework | F1.2, F1.4, F1.5 | Treating web empty states as full dashboards | Org-scoped services + archive lifecycle + lightweight audit_events | Cross-org deny; archive not hard-delete; CI Postgres green |
| F1.7 | Audit log + emergency access | NOT STARTED | None | Audit event model, writer, emergency-access reason and expiry | F1.2, F1.4 | Adding logs only in the Node API will be thrown away | Write from FastAPI on auth and data changes | A reviewed action stores actor, action, record, time; emergency access stores a reason |
| F1.8 | Private file storage | PARTIALLY IMPLEMENTED | `api/src/routes/documents.ts`, `api/src/index.ts` static `/uploads` | Private S3 interface, no public static files, auth on download | F1.5 | Current files are on disk and the static route does not check the token | New storage port plus a tested adapter. Do not point production at `./uploads` | Upload and download succeed for an allowed user and fail for another organisation |
| F1.9 | Web dashboard shell | NOT STARTED | Expo tabs and dashboard components under `room-ready/components/dashboard/` | Next.js app, Tailwind, three role homes | F1.3 | Treating Expo web as the dashboard violates the stack | New `apps/web` shell only. Reuse layout ideas, not the Expo routes, as the admin product | Super Admin, Organisation Admin, and Landlord each reach a signed-in home |
| F1.10 | Occupancy feasibility survey | NOT STARTED | Plan text in `docs/HMore-Proposal-Exact-Implementation-Plan-v1.0.md` | Client survey template: room types, cameras, viewers, retention, accuracy | None in code | Building cameras before the survey | Document only | Template exists and states that camera software is out of scope |
| F1.11 | Encryption, secrets, AWS UK/EU baseline | NOT STARTED | `.gitignore` ignores `.env`. JWT code reads `JWT_SECRET` with a fallback | TLS and at-rest statement, secret manager, AWS region note, removal of the fallback on any new service | Human AWS account decision | A fallback signing key in the reference API is unsafe if copied | Baseline doc in `docs/security` plus task definition for secrets. Do not copy the Node fallback into FastAPI | Document reviewed; new service refuses to boot without a configured secret |

## What is reusable

- Expo navigation, forms, and cards for properties, repairs, documents, messages, and inspections, as a later mobile starting point.
- The idea of central access helpers. The current helpers are property-scoped and must not be copied as organisation security.
- Zod-style request validation, to be repeated with Pydantic.
- The written plan and the Smart Vite prototype spec in `docs/`. The prototype is a screen reference. It is not an implemented HMore backend.

## Security gaps

- No MFA, no managed identity, long-lived local JWT, role chosen at registration.
- Development signing fallback if `JWT_SECRET` is unset.
- Open CORS.
- Uploads exposed through a static path.
- Demo seed password stored in `api/src/seed.ts`.
- No audit trail and no organisation boundary.
- `admin` is global.

## CI and test gaps

`.github/workflows/ci.yml` ran on commit `e67678a`. Both the pull request run `42000186838` and the push run `42000129576` completed with conclusion success. Each run executed:

- Web: `npm ci`, Next lint, `tsc --noEmit`, `next build`, Playwright Chromium smoke tests.
- Mobile typecheck: `tsc --noEmit` in `room-ready`.
- API: `compileall` and Pytest for the health endpoints.
- AI service: `compileall` and Pytest for the LangGraph foundation health check.

Still unverified, and not claimed as passed:

- Docker Compose build and startup.
- Expo runtime (`expo start`).
- Python formatting.
- API integration tests against Postgres.
- Dependency review and secret scanning.
- Allow and deny tests. Those belong to later Phase 1 tasks.

## Git governance

Recorded in `docs/development/GIT_WORKFLOW.md` on 2026-11-05. The seven-phase plan is unchanged.

| Item | State |
| --- | --- |
| Workflow document | On `chore/phase1-git-governance`. Not committed on `main`. |
| `develop` vs `main` | Fast-forward completed. Both `origin/develop` and `origin/main` are `f0a1625`. |
| Branch protection | Active on `main` (pull request and 1 approval) and `develop` (pull request). Force push and deletion blocked. Required status checks are still not enabled. |
| CI | Workflow `.github/workflows/ci.yml` is on this branch. Checks on `e67678a` succeeded. Branch protection still does not require those checks. Docker Compose and Expo runtime were not part of the run. |

## Human decisions

1. Review the pull request from `chore/phase1-git-governance` into `develop`. Do not commit these docs on `main`. The fast-forward of `develop` to `f0a1625` is done.
2. Choose Auth0 or Entra External ID before F1.3.
3. Confirm AWS account and UK or EU region before F1.11 is more than a document.
4. Confirm that Room Ready's `property_manager` and `admin` roles are retired rather than renamed in place.
5. Confirm product branding for the new web shell: HMore as the delivery name, while prototype art still says Smart Vite.

## Readiness

Phase 1 feature coding should not start. The next implementation prompt, after this audit is reviewed on the chore branch, is F1.1 only: repository skeleton and a CI workflow that runs real commands. No tenant, auth, or schema business features in that prompt.
