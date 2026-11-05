# Repository audit

Audit date: 2026-11-05. Branch inspected: `main` at `f0a1625`. No production code was modified. No tests were executed, so nothing in this audit is marked verified by a test run.

## A. Repository structure

The repository is not the target monorepo. It has two applications and a docs folder.

| Path | What it is |
| --- | --- |
| `room-ready/` | Expo SDK 57 mobile app, product name Room Ready. Also starts a web bundle through Expo, not Next.js. |
| `api/` | Node.js + Express 5 + Prisma API, package name `room-ready-api`. |
| `docs/` | Proposal plan, prototype screen spec, and this audit. |
| `.gitignore` | Ignores `node_modules`, `.env`, SQLite files, and `api/uploads`. |

Absent: `apps/`, `packages/`, `infra/`, Python, FastAPI, Next.js, LangGraph, Celery, Redis, Docker, GitHub Actions, Playwright, Pytest, Sentry.

## B. Frontend

`room-ready/package.json` is the mobile app.

- Expo `~57.0.2`, React Native `0.86.0`, React `19.2.3`, TypeScript `~6.0.3` with `strict: true`.
- Routing: Expo Router file routes under `room-ready/app/`. Auth group `(auth)`, app group `(app)`, tabs under `(app)/(tabs)`.
- No Tailwind config. Styling is React Native components plus `constants/theme.ts` and `constants/Colors.ts`.
- Server state: TanStack Query in `contexts/QueryProvider.tsx`. Auth state: `contexts/AuthContext.tsx`.
- API client: `lib/api.ts` sends a bearer token from secure storage (`lib/tokenStorage.ts`, `expo-secure-store`).
- Role gating: `constants/permissions.ts` and `hooks/useRoleGuard.tsx`.
- There is no Next.js web dashboard.

Screens that can be reused as UX reference, not as the HMore web app: properties, rooms, listings, applications, tenancies, maintenance, inspections, documents, messages, notifications, dashboard cards.

`lib/ai.ts` is a local keyword triage function. It is not a LangGraph service and it does not call a model.

## C. Backend

Only the Node API exists. There is no Python or FastAPI code.

`api/src/index.ts` mounts:

`/health`, `/auth`, `/properties`, `/listings`, `/applications`, `/tenancies`, `/maintenance`, `/documents`, `/conversations`, `/notifications`, `/inspections`, `/admin`, `/users`, `/dashboard`.

Patterns that exist:

- Zod validation on several route bodies, including auth.
- JWT bearer middleware in `api/src/middleware/auth.ts`.
- Role helper `requireRoles`.
- Property-scoped access helpers in `api/src/lib/access.ts`.
- JSON error bodies such as `{ error: "..." }`.
- Logging is `console.error` / `console.log`. There is no structured logger and no global error middleware.

This API is reference only. The production backend must be Python + FastAPI.

## D. Database

- Engine: SQLite, declared in `api/prisma/schema.prisma` and locked in `api/prisma/migrations/migration_lock.toml`.
- One migration: `api/prisma/migrations/20260705142627_init`.
- Seed: `api/src/seed.ts` creates demo users and related records.
- No PostgreSQL, no pgvector, no organisation table, no audit-log table, no membership table.

Models: User, Property, Room, Listing, Application, Tenancy, MaintenanceRequest, MaintenanceUpdate, Document, Conversation, ConversationParticipant, Message, Notification, Inspection.

`User.role` is `landlord | tenant | property_manager | contractor | admin`. That is five roles, and they are not the six HMore roles.

Isolation is by property owner, manager, tenancy, or contractor assignment. There is no organisation boundary. The `admin` role loads every property.

## E. Security

Observed risks. Secret values are not copied here.

- Authentication is email and bcrypt password, then a local JWT. There is no Auth0 or Entra External ID, and no MFA.
- `signToken` sets a 30-day expiry.
- A development fallback is used when `JWT_SECRET` is unset (`api/src/middleware/auth.ts`).
- Registration lets the caller choose `landlord`, `tenant`, `property_manager`, or `contractor` (`api/src/routes/auth.ts`).
- CORS is `app.use(cors())` with no origin restriction.
- Uploaded files are stored on local disk and served by `express.static` at `/uploads`. That is not private S3.
- `.gitignore` ignores `.env`. No `.env` file is committed. The seed script contains a shared demo password in source.
- No audit log of who viewed or changed a record.
- No organisation isolation, so a platform-wide admin can read every property.
- No session revocation beyond changing the password. Logout is client-side token deletion.

## F. Testing

No unit, integration, or end-to-end tests were found. No Pytest, Playwright, Jest, or coverage config. No CI job runs tests. This audit did not start the API or the Expo app, so runtime behaviour is not verified.

## G. DevOps

- Remote exists: `origin` = `https://github.com/smartstackdevelopers/hmo-management-app.git`.
- No `.github/workflows`.
- No Dockerfile, compose file, AWS template, Sentry config, or backup job.
- GitHub commit status for `f0a1625` has zero checks.

## Technical debt that blocks Phase 1

1. Wrong primary backend language and database.
2. Wrong role model and no organisation.
3. Local auth instead of managed identity and MFA.
4. Public local uploads instead of private object storage.
5. Mobile-only shell instead of a Next.js admin dashboard.
6. No test or CI baseline.
7. Room Ready domain code cannot be moved into `apps/` until a reviewed migration; this audit does not move it.
