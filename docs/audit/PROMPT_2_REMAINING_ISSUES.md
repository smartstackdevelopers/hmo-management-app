# PROMPT 2 — Remaining issues

**Date:** 2026-11-14 (follow-up)  
**Branch:** `develop` @ `95bed7a`  
**Prompt 3:** Not started.

---

## Overall gate (auth & roles module)

| Item | Verdict |
| --- | --- |
| M01.1 Six roles enforced (code) | **PASS** |
| M01.2 Auth0 login/logout (live) | **PARTIAL** (logout **PASS** in code only) |
| M01.3 Org isolation (automated) | **PASS** |
| M01.6 MFA staff path | **UNVERIFIED** |
| Six-role acceptance checklist | **UNVERIFIED** |

---

## Six-role local verification (manual — no secrets in git)

Complete these steps on your machine. Do **not** commit `apps/api/.env`, `apps/web/.env.local`, `room-ready/.env`, or `scripts/meeting-six-roles.local.env`.

### Prerequisites

| Step | Action |
| --- | --- |
| P1 | PostgreSQL up: `docker compose -f infra/docker/docker-compose.yml up -d postgres` |
| P2 | Migrate: `cd apps/api && alembic upgrade head` |
| P3 | Copy env from `.env.example` files; use one shared `AUTH0_AUDIENCE` (e.g. `https://api.hmore.local`) on API, web, and mobile |
| P4 | Auth0 UK/EU tenant: Regular Web App (web), Native App (mobile), API identifier = audience — see `docs/development/IDENTITY_PROVIDER_SETUP.md` if present, else `FULL_AUTH_ONBOARDING.md` |
| P5 | API on `:8000`, web on `:3000` (optional for mobile-only roles) |

### Create six Auth0 users (Dashboard)

In Auth0 **User Management**, create six users with emails you control (password or connection policy). Record emails only in the **local** env file below — not in git.

### Bootstrap HMore memberships

```powershell
# From repo root
Copy-Item scripts\meeting-six-roles.env.example scripts\meeting-six-roles.local.env
# Edit meeting-six-roles.local.env — set EMAIL_* and MEETING_ORG_SLUG / MEETING_ORG_NAME

.\scripts\bootstrap-all-six-roles.ps1
# Or per role: .\scripts\bootstrap-identity.ps1 grant-super-admin --email you@example.com
```

Verify:

```powershell
cd apps\api
python scripts\bootstrap_identity.py list-roles   # must show exactly 6 roles
python scripts\bootstrap_identity.py show-user --email <your-super-admin-email>
```

### Per-role smoke (fill `docs/development/ROLE_ACCEPTANCE_CHECKLIST.csv`)

| ID | Role | Client | Steps |
| --- | --- | --- | --- |
| R1 | `super_admin` | Web | Open `http://localhost:3000/auth/login` → land on `/dashboard/super-admin` → open `/dashboard/super-admin/organisations` (needs `PLATFORM_GOVERNANCE_GLOBAL_ENABLED=true` in API env) → list/create org → **Logout** via header/account (`/auth/logout`) |
| R2 | `organisation_admin` | Web | Login → `/dashboard/organisation-admin` → open approvals or org settings → core action → logout |
| R3 | `landlord` | Web | Login → `/dashboard/landlord` → property list or create → logout |
| R4 | `support_worker` | Mobile | Auth0 login in Expo → staff home → visit/task screen → sign out (`more` / `settings` / staff UI → `signOut`) |
| R5 | `tenant` | Mobile | Auth0 login → tenant home → maintenance request → sign out |
| R6 | `maintenance_contractor` | Mobile | Auth0 login → contractor view → open work order list → sign out |

### API token checks (optional, with a user logged in on web)

1. Obtain access token (Auth0 test or browser devtools / Auth0 debugger).
2. `GET http://localhost:8000/api/v1/auth/me` — `Authorization: Bearer <token>` → 200, `external_subject` set.
3. `GET http://localhost:8000/api/v1/rbac/me` — same header → 200, `active_role` matches bootstrap.

### Logout verification (manual)

| Client | What to confirm |
| --- | --- |
| Web | After `/auth/logout`, protected `/dashboard` redirects to login; no stale session cookie |
| Mobile | After sign out, SecureStore tokens cleared; re-open app prompts Auth0 login (Auth0 mode) |

Auth0 **Allowed Logout URLs** must include `APP_BASE_URL` and the mobile `returnTo` from `createAuth0RedirectUri` in `room-ready/lib/hmoreAuth0.ts`.

### MFA (staff) — still **UNVERIFIED** until:

1. Auth0 **Security → Multifactor Auth** enabled per `docs/development/MFA_CONFIGURATION.md`.
2. Post-Login Action (or tenant policy) requires MFA for staff web client.
3. Optional: set `AUTH0_REQUIRE_MFA_CLAIM=true` in API `.env` **only after** confirming access token `amr` includes `mfa`.
4. `GET /api/v1/auth/staff-session` returns `"mfa": true` for a staff user who completed MFA.

No MFA **PASS** without your tenant configuration — repo has docs and unit tests only.

---

## Resolved in Prompt 2 commit `95bed7a`

| Item | Status |
| --- | --- |
| `tests/test_organisations_list.py` import fix | **PASS** (committed) |
| Prompt 2 audit quartet | **PASS** (committed) |
| `ROLE_ACCEPTANCE_CHECKLIST.csv` + `meeting-six-roles.env.example` | Tracked in `95bed7a` |

---

## Known gaps (unchanged)

| Issue | Verdict |
| --- | --- |
| Web deep routes not all wrapped in `requireDashboardRole` | **PARTIAL** — API enforces; landlord home has no `requireDashboardRole` in grep (org-admin/super-admin/support-worker/super-org pages do) |
| Mobile legacy auth when Auth0 unset | **PARTIAL** — dev convenience |
| Playwright `npm run test:e2e` | **UNVERIFIED** |
| Expo on device with LAN API URL | **UNVERIFIED** |
| Push to `origin/develop` | Not requested |

---

## What still requires you (summary)

- **Six Auth0 logins** + checklist R1–R6 → **UNVERIFIED**
- **MFA staff policy** on real tenant → **UNVERIFIED**
- **Live logout** end-to-end → **UNVERIFIED**
- **Prompt 3+** feature work → not started