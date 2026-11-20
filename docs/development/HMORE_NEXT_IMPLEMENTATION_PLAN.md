# HMore — next implementation plan (local complete → staging → production)

| Field | Value |
| --- | --- |
| Document version | 1.0 |
| Date | 2026-11-14 |
| Branch focus | `feature/full-auth-onboarding` → `develop` |
| Audience | Implementation lead (local setup, then deploy) |
| Related docs | `FULL_AUTH_ONBOARDING.md`, `MEETING_DEMO_RUNBOOK.md`, `DEPLOYMENT_APPROVAL_GATE.md`, `REMEDIATION_PLAN.md` |

---

## 1. Purpose and success definition

### 1.1 Goal

Deliver a **working HMore system on one real stack** (Auth0 + PostgreSQL + FastAPI + Next.js + Expo with Auth0), with **all six roles** able to sign in and perform their primary workflows. Only after that gate passes, deploy to **staging**, then **production** with client approvals.

### 1.2 What “complete” means for you (Level A — deploy prerequisite)

| In scope (must work locally) | Out of scope (before first deploy) |
| --- | --- |
| Six roles: login, RBAC, main home screen, one core action each | Live room cameras / occupancy ingest (deferred by design) |
| Single API: `apps/api` port **8000** | Legacy `api/` port **3001** (prototype only) |
| Web Auth0 for Super Admin, Org Admin, Landlord, Support Worker (web home) | 100% proposal matrix PASS (currently ~55% strict audit) |
| Mobile Auth0 for Tenant, Support Worker, Contractor | App Store / Play Store LIVE release |
| Org isolation on `demo-housing` (or your slug) | Payment gateway, Twilio voice, optional F8 add-ons |
| Sign-in, sign-out, bootstrap memberships | Organisational DPIA / legal sign-off (required for **public** prod) |
| Smoke tests + role checklist (Section 6) | AWS live until staging wave |

### 1.3 What “production ready” means (Level B — after staging)

- All rows **PASS** or **APPROVED** in `docs/phase7/production/DEPLOYMENT_APPROVAL_GATE.md`
- Staging smoke on HTTPS API URL
- MFA policy enforced for staff/admin on Auth0
- RDS, ElastiCache, private S3, backups verified
- Client owner signature on deployment gate

**Honest baseline (audit):** go-live was **BLOCKED**; deploy only after Level A + staging + gate.

---

## 2. Architecture (one platform — no split brain)

```text
                    ┌─────────────┐
                    │   Auth0     │
                    │  (IdP/MFA)  │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ apps/web   │  │ room-ready │  │  Staff     │
    │ :3000      │  │ (Expo)     │  │  browsers  │
    └─────┬──────┘  └─────┬──────┘  └────────────┘
          │               │
          └───────┬───────┘
                  ▼
          ┌───────────────┐
          │ apps/api      │
          │ FastAPI :8000 │
          └───────┬───────┘
                  ▼
          ┌───────────────┐
          │ PostgreSQL    │
          │ (Docker/RDS)  │
          └───────────────┘
```

**Never run legacy Express + SQLite in parallel for “real” testing** once Level A starts.

---

## 3. Six roles — client and assignment

| Code | Primary client | Web dashboard home | Mobile |
| --- | --- | --- | --- |
| `super_admin` | Web | `/dashboard/super-admin` | N/A |
| `organisation_admin` | Web | `/dashboard/organisation-admin` | Optional |
| `landlord` | Web | `/dashboard/landlord` | Optional |
| `support_worker` | Mobile (staff shell) | `/dashboard/support-worker` if enabled | Staff tabs |
| `tenant` | Mobile (tenant shell) | `/account` (mobile-first) | Tenant tabs |
| `maintenance_contractor` | Mobile | `/account` (mobile-first) | Contractor flows |

Membership is **never** self-assigned in production: use `bootstrap_identity.py` or Super Admin assignment API.

---

## 4. Implementation waves (order is mandatory)

### Wave 0 — Environment lock (1–2 days)

**Objective:** One reproducible local stack.

| Task | Action | Done when |
| --- | --- | --- |
| W0.1 | Docker Desktop runs; `scripts/setup-local-windows.ps1` succeeds | `docker ps` shows postgres healthy |
| W0.2 | `apps/api/.env` has `DATABASE_URL`, `AUTH0_*` | `GET /health` returns OK |
| W0.3 | `apps/web/.env.local` has Auth0 + `APP_BASE_URL=http://localhost:3000` | Login redirects to Auth0 |
| W0.4 | `alembic upgrade head` | No migration errors |
| W0.5 | Stop using `api/` :3001 for HMore tests | No dependency on SQLite demo |
| W0.6 | Document PC LAN IP for phone (`ipconfig`) | Mobile `.env` updated |

**Commands (reference):**

```powershell
cd "D:\hmore app"
.\scripts\setup-local-windows.ps1
cd apps\api
..\..\.venv\Scripts\alembic upgrade head
..\..\.venv\Scripts\uvicorn app.main:app --reload --port 8000
# separate terminal:
cd "D:\hmore app"
npm run web:dev
```

---

### Wave 1 — Identity: six Auth0 users + bootstrap (2–3 days)

**Objective:** Every role exists in Auth0 **and** PostgreSQL.

| Task | Action |
| --- | --- |
| W1.1 | Create **six users** in Auth0 Dashboard (unique emails, verified). |
| W1.2 | Auth0 Application: callback `http://localhost:3000/auth/callback`, logout `http://localhost:3000`, API audience matches `AUTH0_AUDIENCE`. |
| W1.3 | Create **Native application** for Expo: set `EXPO_PUBLIC_AUTH0_CLIENT_ID`, domain, audience in `room-ready/.env`. |
| W1.4 | Run bootstrap for each email (org slug e.g. `demo-housing`). |
| W1.5 | Each user logs in once (web or mobile) to link `external_subject`. |
| W1.6 | Verify `GET /api/v1/rbac/me` with token per role. |

**Bootstrap template (from `apps/api`, venv python):**

```text
python scripts/bootstrap_identity.py grant-super-admin --email <super@example.com>
python scripts/bootstrap_identity.py grant-org-role --email <super@example.com> --role organisation_admin --org-slug demo-housing --org-name "Demo Housing"
python scripts/bootstrap_identity.py grant-org-role --email <landlord@example.com> --role landlord --org-slug demo-housing
python scripts/bootstrap_identity.py grant-org-role --email <oa@example.com> --role organisation_admin --org-slug demo-housing
python scripts/bootstrap_identity.py grant-org-role --email <tenant@example.com> --role tenant --org-slug demo-housing
python scripts/bootstrap_identity.py grant-org-role --email <support@example.com> --role support_worker --org-slug demo-housing
python scripts/bootstrap_identity.py grant-org-role --email <contractor@example.com> --role maintenance_contractor --org-slug demo-housing
python scripts/bootstrap_identity.py show-user --email <each>
```

**Optional automation:** copy `scripts/meeting-six-roles.env.example` → `meeting-six-roles.local.env` and run `scripts/bootstrap-all-six-roles.ps1`.

**Automated checks:**

```powershell
cd apps\api
..\..\.venv\Scripts\pytest -q tests/test_identity_bootstrap.py tests/test_auth_tokens.py tests/test_rbac_registry.py
```

---

### Wave 2 — Seed data and cross-role workflows (3–5 days)

**Objective:** Screens are not empty; one journey works end-to-end.

| Task | Data / workflow |
| --- | --- |
| W2.1 | Organisation `demo-housing` visible to Super Admin |
| W2.2 | At least **1 property**, **1 room** (landlord or API) |
| W2.3 | Link **tenant** user to tenancy / tenant record |
| W2.4 | **Maintenance:** tenant creates request → landlord/contractor sees it |
| W2.5 | **Housing application** OR **complaint** (one full create → list → detail) |
| W2.6 | **Document** upload metadata (files adapter — local/minio if configured) |
| W2.7 | Support worker: **visit** or **task** create (mobile or API) |

**Reference test (automation exists in repo):** Ali journey — `test_f215_ali_end_to_end.py` (run in CI/postgres when available).

**Manual E2E script (minimum):**

1. Tenant (mobile): report repair.  
2. Landlord (web): sees maintenance item.  
3. Contractor (mobile): assigned path or list access.  
4. Org Admin (web): approvals inbox if workflow enabled.  
5. Super Admin (web): audit or organisations — no cross-org leak.

---

### Wave 3 — Mobile parity (2–4 days)

**Objective:** Mobile uses **only** HMore API + Auth0.

| Task | Action |
| --- | --- |
| W3.1 | Remove/unset legacy `EXPO_PUBLIC_API_URL` (3001) |
| W3.2 | `EXPO_PUBLIC_HMORE_API_URL=http://<LAN-IP>:8000/api/v1` on physical device |
| W3.3 | Auth0 Native allowed callback URLs for Expo (`roomready://auth/callback` or generated redirect URI) |
| W3.4 | Test sign-in, sign-out, biometric gate (if enabled), offline drafts not blocking logout |
| W3.5 | Push: optional locally; do not block Level A on push |

---

### Wave 4 — Web module smoke (2–3 days)

**Objective:** Sidebar modules load without 500 for **Org Admin + Landlord** (spot-check 10 highest-value routes).

| Area | Routes to open (examples) |
| --- | --- |
| Housing | `/dashboard/housing-applications`, `/dashboard/waiting-list` |
| Operations | `/dashboard/maintenance`, `/dashboard/complaints` |
| People | `/dashboard/caseload/...`, `/dashboard/support-worker` |
| Documents | `/dashboard/documents` |
| Comms | `/dashboard/communications/inbox` |
| Reports | `/dashboard/reports` |
| Governance | `/dashboard/audit` (role permitting) |

Log failures in a simple tracker (role, URL, HTTP status, screenshot).

---

### Wave 5 — Quality gate “Level A complete” (1 day)

**Exit criteria (all must be checked):**

- [ ] 6/6 roles login successfully  
- [ ] Legacy 3001 not required for any demo  
- [ ] Web and mobile sign-out works  
- [ ] `pytest` smoke (Wave 1) green  
- [ ] Section 6 role checklist 100%  
- [ ] Known gaps documented (Section 8)  
- [ ] PR merged: onboarding + org UI + auth fixes on `develop`  

**Sign-off:** Technical lead + product owner (informal for local; formal before staging).

---

### Wave 6 — Staging deploy (1–2 weeks, client-dependent)

**Objective:** HTTPS environment mirroring local, no public marketing until smoke passes.

| Step | Reference |
| --- | --- |
| S6.1 | Client approves AWS region (`eu-west-2`), domain, Terraform apply (`REMEDIATION_PLAN` R1) |
| S6.2 | Production-like env files (secrets in vault, not Git) |
| S6.3 | Auth0 staging apps: callbacks for `https://staging.<domain>` |
| S6.4 | Run `FULL_AUTH_ONBOARDING.md` smoke on staging URLs |
| S6.5 | Re-run **Section 6 role checklist** on staging |
| S6.6 | Celery + Redis in staging (scheduled jobs) — `R12` |
| S6.7 | MFA enabled for staff paths — `R2` |

---

### Wave 7 — Production go-live (after gate only)

| Step | Reference |
| --- | --- |
| S7.1 | `DEPLOYMENT_APPROVAL_GATE.md` — all rows PASS/APPROVED + signatures |
| S7.2 | Backup/restore drill — `R8` / F7.3 |
| S7.3 | DPIA / security sign-off — R3, R9 |
| S7.4 | EAS store submit — R5 / F7.7 |
| S7.5 | Sentry + runbooks — R11, R13 |
| S7.6 | `SMOKE_TEST_SCRIPT.md` post-deploy |

---

## 5. Role acceptance checklist (printable)

Use one row per tester. **Pass** = action completes without wrong-role access.

| ID | Role | Login path | Home / first screen | Core action | Sign out | Pass |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | super_admin | Web `/auth/login` | Super Admin home | Create/list organisation | Log out | ☐ |
| R2 | organisation_admin | Web | Org Admin home | Open approvals or users | Log out | ☐ |
| R3 | landlord | Web | Landlord home | Open/create property | Log out | ☐ |
| R4 | support_worker | Mobile Auth0 | Staff account tab | Open visits/tasks | Sign out | ☐ |
| R5 | tenant | Mobile Auth0 | Tenant home | Create maintenance request | Sign out | ☐ |
| R6 | maintenance_contractor | Mobile Auth0 | Staff/contractor view | View/update work order | Sign out | ☐ |

**API spot check (any role with token):** `GET /api/v1/auth/me`, `GET /api/v1/rbac/me` → 200, correct `active_role`.

---

## 6. Timeline estimate (single developer, focused)

| Wave | Duration | Cumulative |
| --- | --- | --- |
| 0 Environment | 1–2 days | 2 days |
| 1 Identity (6 roles) | 2–3 days | 5 days |
| 2 Seed + E2E | 3–5 days | 10 days |
| 3 Mobile | 2–4 days | 14 days |
| 4 Web smoke | 2–3 days | 17 days |
| 5 Gate Level A | 1 day | **~3 weeks** local complete |
| 6 Staging | 1–2 weeks | + client/AWS |
| 7 Production | 2–4 weeks | + legal/ops |

Parallel work possible if mobile and web split between two developers (shave ~1 week).

---

## 7. Repository deliverables (implementation artefacts)

| Artefact | Path | When |
| --- | --- | --- |
| This plan | `docs/development/HMORE_NEXT_IMPLEMENTATION_PLAN.md` | Now |
| PDF export | `docs/development/HMORE_NEXT_IMPLEMENTATION_PLAN.pdf` | Generated |
| Full auth checklist | `docs/development/FULL_AUTH_ONBOARDING.md` | Wave 1 |
| Six-role bootstrap script | `scripts/bootstrap-all-six-roles.ps1` | Wave 1 |
| Email template | `scripts/meeting-six-roles.env.example` | Wave 1 |
| Role checklist CSV | `docs/development/ROLE_ACCEPTANCE_CHECKLIST.csv` | Wave 5 |
| Local demo links | `docs/development/LOCAL_DEMO_LINKS.md` | Wave 0 |

---

## 8. Known gaps to track (do not hide)

| Gap | Impact on Level A | When to fix |
| --- | --- | --- |
| Proposal 55% strict PASS | Does not block local Level A | Post-staging remediation R14–R19 |
| Occupancy live cameras | Off by design | After per-org DPIA |
| SMS/email providers | In-app comms OK; external channels mock | Staging keys |
| App stores | Expo Go / dev build OK | Wave 7 |
| PARTIAL optional F8 UI | Pages may be empty states | Client scope decision |
| MFA production enforce | Local login works | Staging R2 |

---

## 9. Risk register (short)

| Risk | Mitigation |
| --- | --- |
| Docker/WSL fails on Windows | `DOCKER_WSL_FIX_WINDOWS.md`; use `setup-local-windows.ps1` |
| Mobile cannot reach API | LAN IP, firewall, same Wi‑Fi |
| Auth0 email not in token | Auth0 Action adds `email` claim |
| Empty dashboard after login | Bootstrap + one web login to link `sub` |
| Scope creep (“100% proposal before deploy”) | Stick to Level A definition (Section 1.2) |

---

## 10. Weekly execution template

**Week focus:** _______________  
**Wave:** _______________

| Mon | Tue | Wed | Thu | Fri |
| --- | --- | --- | --- | --- |
| | | | | |

**Done this week:**  
**Blockers:**  
**Next week wave:**

---

## 11. UI/UX redesign — Blue & White (implementation track)

The approved visual direction is the **Blue & White edition** of the design spec. It is implemented screen by screen, exactly as drawn, on its own branch. The design spec is the source of truth for layout, copy and states. This track changes presentation only: API contracts, permissions and RBAC stay the same.

| Field | Value |
| --- | --- |
| Design reference | `docs/audit/HMORE_UI_UX_DESIGN_SPEC_COMPLETE_BLUE.pdf` (74 pages · 60 mobile + 44 web screens) |
| Screen index | `docs/audit/HMORE_UI_UX_DESIGN_SPEC_COMPLETE_BLUE.md` |
| Branch | `feature/phase8-ui-ux-blue-white` (from `feature/p12-native-auth-local`) → PR into `develop` |
| Scope | Local only. No deploy, store release or paid services. |
| Alternative | The Teal edition (`HMORE_UI_UX_DESIGN_SPEC_COMPLETE.pdf`) is kept for reference only. |

### 11.1 Design tokens (shared by web and mobile)

| Token | Value | Web (Tailwind) | Mobile (`room-ready/constants/theme.ts`) |
| --- | --- | --- | --- |
| Primary | `#1D4ED8` Blue 700 | `brand-700` (alias `teal-700`) | `secondaryDark`, `tabBarActive` |
| Primary hover / accent | `#2563EB` Blue 600 | `brand-600` | `secondary`, `accent` |
| Soft accent | `#EFF6FF` / `#DBEAFE` | `brand-50` / `brand-100` | `accentLight` / `accentSoft` |
| Brand | `#172554` Navy 950 | `navy-900` (alias `forest-900`) | `brand` |
| Background | `#F3F7FD` | `cream` | `background` |
| Surface | `#FFFFFF` | `white` | `surface` |
| Border | `#DFE6F1` | `slate-200` | `border` |
| Info | `#4F46E5` Indigo | `indigo-*` | `info` |
| Success / warning / danger | `#059669` / `#D97706` / `#DC2626` | `emerald` / `amber` / `red` | unchanged |

### 11.2 Waves and status

| Wave | Scope | Screen IDs | Status |
| --- | --- | --- | --- |
| UI-0 | Tokens, brand mark, white grouped collapsible sidebar, header (role chip, search), empty / error / loading states, page header | §3, W-MD-13, M-GS | **Done** (branch) |
| UI-1 | Authentication: split-screen sign in, request access (role cards), pending timeline; friendly error copy; demo login only in local dev | W-AU-01…03, M-AU-03 | **Done** (web + mobile pending) · mobile M-AU-01/02/04–06 next |
| UI-2 | Role homes / dashboards: KPI cards, attention list, tables | W-SA-01, W-OA-01, W-LL-01, W-SW-01, W-CT-01, W-TN-01, M-*-01 | Next |
| UI-3 | Core operations: properties, repairs, messages, documents, inspections | M-TN, M-LL, M-CT, M-MS, M-DC, M-IN, W-LL, W-CT, W-MD-01/02 | Planned |
| UI-4 | Support, safety & community: caseload, logs, incidents, community, employment, wellbeing | M-SW, M-CM, M-EM, M-WB, W-SW, W-MD-03…07 | Planned |
| UI-5 | Admin, insights & polish: approvals, reports, finance, automation, settings; accessibility pass | M-OA, M-SA, M-ST, W-SA, W-OA, W-MD-08…12 | Planned |

### 11.3 Rules for every UI wave

- Match the Blue & White mockup for the Screen ID (layout, hierarchy, copy, states).
- Use only tokens and shared components (`components/dashboard/*`, `components/auth/AuthShell`, mobile `components/ui/*`).
- Primary action is the only blue filled button on the screen.
- Never show raw API text; use `lib/authErrors.ts`-style friendly copy.
- Keep nav item `id`s and permission filters unchanged (tests depend on them; hiding a link is not security).
- Checks before each commit: `npm run typecheck` and `npm run lint` in `apps/web`, `npx tsc --noEmit` in `room-ready`, plus a screenshot of each changed screen.

---

## 12. Approval

| Role | Name | Date | Signature |
| --- | --- | --- | --- |
| Implementation lead | | | |
| Project owner | | | |

---

*End of document — HMore Next Implementation Plan v1.0*