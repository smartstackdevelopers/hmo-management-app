# Phase 1 readiness report

Assessment date: 2026-11-05. Readiness: **not ready to implement Phase 1 features**. Governance is blocked until `develop` is fast-forwarded to `main`. No Phase 1 deliverable is verified.

Status values used: NOT STARTED, PARTIALLY IMPLEMENTED, IMPLEMENTED BUT UNVERIFIED, VERIFIED. Nothing is VERIFIED. No automated test was run.

## Coverage matrix

| ID | Requirement | Status | Existing files | Missing work | Dependencies | Risks | Approach | Acceptance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1.1 | Monorepo + CI/CD | NOT STARTED | `room-ready/`, `api/`, root `.gitignore` | Target folders, GitHub Actions, Pytest, Playwright | `develop` aligned with `main` | Moving Expo too early breaks the only client | Add new folders and a real workflow beside current apps | Workflow runs on a pull request and reports the jobs it actually contains |
| F1.2 | PostgreSQL schema + migrations | NOT STARTED | `api/prisma/schema.prisma`, `api/prisma/migrations/20260705142627_init` | Postgres, pgvector availability, Phase 1 entities, new migrations | F1.5 role and organisation decisions | Reusing SQLite models would keep the wrong roles | New schema in FastAPI. Keep Prisma as reference | Migration applies on empty Postgres and is reviewed |
| F1.3 | Managed identity + MFA | NOT STARTED | `api/src/routes/auth.ts`, `api/src/middleware/auth.ts`, `room-ready/contexts/AuthContext.tsx` | Auth0 or Entra, MFA, no local password as the primary login | Human choice of provider | Local register-and-role flow would remain if left in place | New login path only. Do not add a fake MFA field | Staff and admin sign-in requires the provider MFA challenge |
| F1.4 | Six roles, permissions, sessions | PARTIALLY IMPLEMENTED | `api/prisma/schema.prisma` `UserRole`, `api/src/lib/access.ts`, `api/src/middleware/auth.ts`, `room-ready/constants/permissions.ts` | The six HMore roles, a permission matrix, session timeout and revocation | F1.3 | Current five roles do not match the plan. `admin` can read all properties | Replace the enum in the new schema. Do not alias `property_manager` to Organisation Admin without a written decision | Deny tests fail closed for every role that must not pass |
| F1.5 | Organisation isolation + membership | NOT STARTED | Property owner and manager fields only | Organisation, membership, per-request organisation scope | F1.2, F1.4 | Property-level filters will leak across organisations | `organisation_id` on tenant-owned rows and tests that use two organisations | A user in org A cannot read org B |
| F1.6 | Tenant and property/room CRUD | PARTIALLY IMPLEMENTED | `api/src/routes/properties.ts`, `tenancies.ts`, `users.ts`, Expo property screens | FastAPI versions, organisation scope, audit on write, tenant record that is not only a login role | F1.2, F1.4, F1.5 | Current CRUD is the wrong stack and the wrong tenancy model | Reimplement baseline create/read/update. Leave listings and applications for later phases | Create tenant and property in one org, see an audit row, deny the other org |
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

No tests and no workflows exist. Recommended pipeline, not active:

- Format and lint for Python and TypeScript.
- Type check.
- Pytest for the FastAPI app, including allow and deny cases.
- Playwright for the Next.js shell once a page exists.
- API integration tests against Postgres.
- Build of web and API.
- Dependency review and secret scanning.
- Pull request workflow on `develop`.

Do not mark any of those active until a run is visible on GitHub.

## Git governance

Recorded in `docs/development/GIT_WORKFLOW.md` on 2026-11-05. The seven-phase plan is unchanged.

| Item | State |
| --- | --- |
| Workflow document | Written, not committed. Working tree is `main` with untracked `docs/architecture`, `docs/audit`, and `docs/development`. |
| `develop` vs `main` | `origin/develop` is `d889dbc`. `origin/main` is `f0a1625`. Count `0	1`. Fast-forward is possible and has not been run. |
| Branch protection | Not verified. Protection API returned 401. GitHub CLI is not installed. |
| CI | Not configured. No status checks to require yet. |

## Human decisions

1. Approve the fast-forward of `develop` to `main`, then commit these docs on `chore/phase1-git-governance` and review them into `develop`. Do not commit them on `main`.
2. Choose Auth0 or Entra External ID before F1.3.
3. Confirm AWS account and UK or EU region before F1.11 is more than a document.
4. Confirm that Room Ready's `property_manager` and `admin` roles are retired rather than renamed in place.
5. Confirm product branding for the new web shell: HMore as the delivery name, while prototype art still says Smart Vite.

## Readiness

Phase 1 feature coding should not start. The next implementation prompt, after this audit is reviewed on the chore branch, is F1.1 only: repository skeleton and a CI workflow that runs real commands. No tenant, auth, or schema business features in that prompt.
